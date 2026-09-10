---
title: 'Loop-home readiness is defined for the cutover flip'
type: 'chore'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      No audit trail (checklist or sign-off log) proves the three manual-only readiness
      items (R1, R2, R5) were actually checked for each of the eight loop homes.
    evidence: |-
      Real gap, but out of this Effort-S/docs story's scope -- the AC asks for the
      readiness items, their proving checks, and the runner, not a new record-keeping
      artifact. A future story could add a per-home sign-off log.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh/loop-home-cutover-readiness.md
    severity: low
  - summary: >-
      No failure/rollback guidance for the attended, eight-times-repeated re-provisioning
      procedure if a readiness check fails partway through.
    evidence: |-
      Real but not requested by the AC; a design question for whoever builds steward
      44.12's mechanism, not this readiness-definition doc.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh/loop-home-cutover-readiness.md
    severity: low
  - summary: >-
      The readiness doc's field-name citations against marshal's live code (e.g. which
      HomeFacts fields marshal homes --json actually serializes) are not wired to any
      test, so a future rename could silently invalidate them.
    evidence: |-
      Real but generic to any hand-written doc citing code shape; no specific
      actionable fix within this docs-only story's scope -- adding a self-verifying
      test is a different, larger story.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh/loop-home-cutover-readiness.md
    severity: low
baseline_revision: '6ba6bd9eb68c35c971c4f90e654ad6423c29951d'
---

<intent-contract>

## Intent

**Problem:** `cutover-readiness.md` G10/P16 (owned by pyforge-steward's `spec-bmad-suite-lifecycle`)
name loop-home readiness as undefined: nobody has written what the eight
`~/.bmad-loops/pyforge-*` homes must contain AFTER the python-foundry cutover flip (each is
currently a full worktree with its own `pixi.toml`, `pyforge.toml` (`name = "local-recipes"`),
`_bmad/` and `_bmad-output/`, pointed at THIS repo). Steward 44.12 will build the re-provisioning
mechanism, but has nothing to build against. Separately, `DW-CC-2026-09-04-1` calls the same
eight homes "residue... retired at Phase 6, never moved" — worded as if they simply disappear,
which needs reconciling with P16's "re-provisioned" framing (they don't disappear; they get
torn down and rebuilt against the new remote).

**Approach:** Write the readiness definition as a companion doc under
`spec-loop-home-fleet-refresh/` (the draft spec already governing loop-home lifecycle; chosen
over inventing a new spec since it is a `docs`-type story and this spec's `surface: []` frontier
status means adding a companion doc requires no governance-list edit). Add a short pointer from
`architecture-bmad-infra.md` § Loop homes. Relay the readiness definition to steward via a memlog
note in `spec-bmad-suite-lifecycle/.memlog.md` (the direct governing spec of `cutover-readiness.md`)
so steward's own memlog-is-the-writer convention can flip G10/P16's state column. Reconcile
`DW-CC-2026-09-04-1`'s "retired" wording in the same companion doc.

## Boundaries & Constraints

**Always:** Name every readiness item as a concrete, checkable fact (what must be true), the
check that proves it (an existing command/field — `marshal homes --json`, `bmad-loop validate`,
manual inspection — never a new detector invented for this docs-only story), and who runs it
(attended, per P16 — steward 44.12's flip, not an automated gate).

**Never:** Do not hand-edit `cutover-readiness.md` directly (steward's file; P4's "memlog is the
single writer" convention applies) — relay via memlog note instead. Do not build steward 44.12's
re-provisioning mechanism (mechanism ships there; this story only defines the target state). Do
not add a new `marshal homes` field, detector, or CLI flag — Effort S / Type docs; the existing
checks are sufficient to name.

## Code Map

- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh/SPEC.md`
  -- `status: draft`, `surface: []` (a frontier, not yet decomposed) — CAP-1 (staleness detection)
  is the only capability written so far; readiness-for-cutover is a distinct concern from
  staleness-refresh, so it lands as a NEW companion doc alongside `SPEC.md`, not inside it.
- `architecture-bmad-infra.md` lines ~855-880 (`### Loop homes — scripts/bmad-loop-worktree`) --
  documents `DEFAULT_LOOP_HOME_ROOT = ~/.bmad-loops/<slug>`, `--verify`/`--list`, the Tier-3
  backlink invariant; add a short pointer to the new companion doc, no duplication.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py:1034` (`run_homes`) +
  `core/status.py:90` (`HomeFacts`) -- `marshal homes --json` proves: `marker_text` (branch-derived
  slug agreement), `symlink_target` (planning-artifacts link), `tier3_local_realpath` vs
  `tier3_canonical_realpath` (Tier-3 backlink), `link_occupied`, `tier3_canonical_is_dir`. Does
  NOT check: remote URL, `pyforge.toml` contents, rendered-policy contents, or in-flight-run
  state -- those items are proven by other named checks or by attended manual inspection.
  Confirmed no existing marshal code reads `pyforge.toml` (`grep -rln "pyforge.toml"
  src/shared/packages/pyforge-marshal/src/` -- zero hits) -- that item is manual inspection.
  `pyforge.toml` itself (repo root) is a single `[project] name = "local-recipes"` scaffold.
- `bmad-loop validate` -- established elsewhere in this fleet (era-alignment memlog CAP-12:
  "`test_harness_policy_render` asserts `bmad-build-auto`; `bmad-loop validate` 8/8 after
  re-render") as the check that proves a loop-home's rendered `.bmad-loop/policy.toml` names the
  live harness skill.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/cutover-readiness.md`
  lines 27 (P16), 44 (G10) -- the rows this story's relay note targets; NOT edited directly (out
  of Surface, steward-owned).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/.memlog.md:46`
  -- existing precedent: a "(note) ... relay from spec-bmad-suite-lifecycle CAP-9" entry already
  forward-references "G10 loop-home readiness → marshal Story 31.5" — confirms cross-project
  memlog relay notes are an established pattern in this fleet, and that `spec-bmad-suite-lifecycle`
  is the direct governing spec of `cutover-readiness.md` (its own header: "Companion of
  `spec-bmad-suite-lifecycle` (CAP-9)").
- `_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md:2571-2576`
  (`DW-CC-2026-09-04-1`) -- "Worktree residue... 8 loop homes... retired at Phase 6, never moved
  (fnd:AD-1)." The wording to reconcile: "retired" (this DW entry) and "re-provisioned" (P16) both
  describe the SAME operation on the SAME eight homes -- tear down the old (pointed at
  `local-recipes`), stand up fresh worktrees at the same slugs (pointed at the new foundry remote)
  -- not a silent disappearance and not a no-op re-point.

## Tasks & Acceptance

**Execution:**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh/loop-home-cutover-readiness.md`
  -- NEW companion doc: the readiness definition (what a re-provisioned home must contain, the
  check that proves each item, who runs it, the DW-CC-2026-09-04-1 reconciliation)
  -- add `companions: [loop-home-cutover-readiness.md]` to `SPEC.md` frontmatter
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh/.memlog.md`
  -- append an entry recording the companion doc's addition (the "or ... memlog note" the
  story's Surface line calls for)
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md`
  -- § Loop homes gains one short paragraph pointing at the new companion doc
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md`
  -- append a relay note: readiness definition done, pointer to the companion doc, so steward's
  own memlog-is-the-writer convention can flip G10/P16's state column

**Acceptance Criteria:**
- Given the eight loop homes are full worktrees with their own `pixi.toml`, `pyforge.toml`, `_bmad/`
  and `_bmad-output/`, when the readiness doc is written, then it names what a re-provisioned home
  must contain after the flip (remote points at the new foundry repo; `pyforge.toml`'s
  `[project] name` matches the foundry repo's name, not `local-recipes`; the rendered
  `.bmad-loop/policy.toml` names `bmad-build-auto`; the `_bmad-output` planning/implementation
  relays are refreshed against the new tree; no run is in flight for that home)
- Given each item, when the doc names the check that proves it, then every check is an EXISTING
  command/field (`marshal homes --json`'s marker/symlink/backlink fields, `bmad-loop validate`,
  manual `git remote -v` / `cat pyforge.toml` inspection, `marshal status` / `bmad-loop status`
  for in-flight state) — no new detector is invented
- Given P16 says this is attended, when the doc names who runs it, then it states steward 44.12's
  flip performs the re-provisioning by hand/attended, not an unattended gate
- Given `DW-CC-2026-09-04-1`'s "residue... retired at Phase 6, never moved" wording, when the doc
  reconciles it, then it states plainly that "retired" and "re-provisioned" describe the same
  tear-down-and-recreate operation on the same eight homes, not a disappearance
- Given `cutover-readiness.md` is steward-owned, when this story closes, then G10/P16 are NOT
  hand-edited directly; a relay note lands in `spec-bmad-suite-lifecycle/.memlog.md` instead

## Spec Change Log

## Review Triage Log

### 2026-09-06 — Review pass
- verdicts: 16 findings — high 5, medium 2, low 5, false 4, maybe-false 0
- findings:
  - `[high]` `[patch]` (blind-hunter) R4's claim that the rendered `.bmad-loop/policy.toml` should name `bmad-build-auto` is already-known-false — evidence: confirmed live (`~/.bmad-loops/pyforge-marshal/.bmad-loop/policy.toml:66` reads `skill = "bmad-dev-auto"`) and confirmed against `bmad_loop`'s installed source (`policy.py:44` `DEV_SKILLS = {"bmad-dev-auto"}`, a hard-validated permanent literal); the correction is already recorded in the very memlog file this diff appends to (`spec-bmad-suite-lifecycle/.memlog.md`, the entry immediately preceding this diff's new line). Grouped with the edge-case-hunter claim below (same root cause).
  - `[false]` `[reject]` (blind-hunter) `SPEC.md`'s `companions:` field looks hand-edited rather than `bmad-spec`-re-derived, against `AGENTS.md:19`'s "never hand-edit SPEC.md" rule — evidence: refuted by extensive established precedent in this exact spec family — Story 31.4 (the immediately preceding story in this same batch) made the identical shape of edit (`surface:` list, one line, paired with a memlog entry, no full re-render) to a different spec's `SPEC.md`, and steward's own memlog history shows the same pattern repeatedly (e.g. "(decision by steward) 2026-09-06 surface widened: + ...spec-template.md"). In this codebase's actual practice, a small structural frontmatter-list edit paired with a memlog entry is the accepted convention.
  - `[high]` `[patch]` (blind-hunter) the doc's Scope section describes steward Story 44.12 as tearing down each loop-home worktree and standing up a fresh one — evidence: read Story 44.12 verbatim in `pyforge-steward/planning-artifacts/epics.md:2685-2693` — it is a `pyforge.cutover_root` **config flag** whose value alone decides "the ledger of record, Mason's targets and the loop-home remotes, and flipping it back restores them" (explicitly reversible) — a flag-driven remote/target change, not a physical destroy-and-recreate. Line 2619 confirms "the eight loop homes re-provisioned against the foundry remote" happens AS PART OF the flag flip, not as a separate manual worktree rebuild.
  - `[medium]` `[patch]` (blind-hunter) the claim that "`cutover-readiness.md`'s G10/P16 state column is flipped by steward's own memlog-is-the-writer convention" overstates the mechanism — evidence: `cutover-readiness.md`'s own P4 row scopes that convention to *SPEC.md* specifically ("No hand-edited SPEC.md; memlog is the single writer"); `cutover-readiness.md` is a companion doc, and its own State column entries (e.g. P8's "satisfied (99e595cc6a)") read like direct hand-updates as work lands, not memlog-driven regeneration. Soften to: this relay note gives steward what it needs to update the State column, by whatever means steward's own process uses.
  - `[high]` `[patch]` (blind-hunter + edge-case-hunter, claim) R3 cites raw `HomeFacts` field names (`marker_text`, `symlink_target`, `tier3_local_realpath`, `tier3_canonical_realpath`, `link_occupied`, `tier3_canonical_is_dir`) as what `marshal homes --json` exposes — evidence: read `_evaluate_home` in `core/status.py:290-297` directly — the actual JSON row only carries `path`, `branch`, `slug`, `active_project`, `desynced` (a computed boolean); the raw `HomeFacts` fields are internal and never serialized. R3 needs to cite the real output shape.
  - `[low]` `[defer]` (blind-hunter) no audit trail (checklist/sign-off log) proving each of the three manual-only items was actually checked per home — evidence: real gap, but out of this Effort-S/docs story's scope — the AC asks for the readiness items, the proving checks, and the runner, not a new record-keeping artifact. `severity: low`.
  - `[low]` `[defer]` (blind-hunter) no failure/rollback guidance for the attended, eight-times-repeated procedure — evidence: real but not requested by the AC; a design question for whoever builds steward 44.12's mechanism, not this readiness-definition doc. `severity: low`.
  - `[low]` `[patch]` (blind-hunter + intent-alignment D4) the reconciliation section quotes `DW-CC-2026-09-04-1`'s "retired... never moved" as if it describes only the eight loop homes, when the ledger entry is actually an aggregate of 268 worktrees across six categories (of which "8 loop homes" is one line-item) — evidence: read `deferred-work-ledger.md:2571-2576` directly. Add a qualifying clause scoping the reconciliation to that one line-item.
  - `[medium]` `[patch]` (edge-case-hunter) both memlog appends (`spec-loop-home-fleet-refresh/.memlog.md` and `spec-bmad-suite-lifecycle/.memlog.md`) left their frontmatter `updated:` timestamp unchanged — evidence: `_bmad/scripts/memlog.py:116-119`'s own `touch()` helper exists specifically to stamp `updated` on every append ("keep it last so the field order stays predictable"); both files' `updated:` still read their pre-existing values after a real content append.
  - `[false]` `[reject]` (intent-alignment, D1) only R3/R4 land on the AC's named check-surface pair; R1/R2/R5 are manual, R6 lands on an adjacent unnamed surface — evidence: the story's own Type (docs) and Effort (S) signal a prose deliverable, and the doc is transparent about which items have no CLI/JSON surface today rather than silently overclaiming coverage — this matches Reading A, which the story's own metadata supports over the stricter Reading C.
  - `[low]` `[defer]` (intent-alignment, D2) the doc's field-name citations aren't wired to any test, so a future rename could silently invalidate them — evidence: real but generic to any hand-written doc citing code shape; no specific actionable fix within this docs-only story's scope (adding a self-verifying test is a different, larger story). `severity: low`.
  - `[false]` `[reject]` (intent-alignment, D3) `cutover-readiness.md` itself is not edited by this diff — evidence: this is BY DESIGN per the story's own Surface line ("via steward memlog relay") and the AC's explicit boundary against hand-editing steward's file; not a defect.
  - `[false]` `[reject]` (intent-alignment, D5) `fnd:AD-12`/`AD-17`'s own text doesn't literally mandate this doc's specific six-item shape — evidence: expected and unavoidable for any decomposition of a high-level architecture decision into concrete readiness items; not a defect.

### 2026-09-09 — Review pass (follow-up)
- verdicts: 24 findings — high 2, medium 1, low 8, false 7, maybe-false 0, defer 6
- findings:
  - `[high]` `[patch]` (blind-hunter) `epics.md:2688-2693` cited for Story 44.12 points at Windows-native story text, not the cutover-flag story — evidence: steward `epics.md:2706-2715` is Story 44.12; fixed to full path + correct lines.
  - `[high]` `[patch]` (blind-hunter) `deferred-work-ledger.md:2571-2576` cited for `DW-CC-2026-09-04-1` points at the wrong ledger row — evidence: entry lives at steward `deferred-work-ledger.md:2591-2598`; fixed.
  - `[medium]` `[patch]` (blind-hunter + edge-case-hunter) R3 names "expected slug" without defining it — evidence: added definition as `~/.bmad-loops/` directory basename with the eight `pyforge-*` station tokens named.
  - `[low]` `[patch]` (blind-hunter) Reconciliation omits that `DW-CC-2026-09-04-1` is `status: resolved` — evidence: ledger row verified `resolved` 2026-09-08; added historiographic note.
  - `[low]` `[patch]` (blind-hunter + edge-case-hunter) R6 cites fleet-wide `marshal status` / bare `bmad-loop status` without per-home scoping — evidence: R6 now names `marshal status --project <slug>` and `bmad-loop status <run_id>`.
  - `[low]` `[defer]` (blind-hunter) parent `SPEC.md` says nine loop homes while companion says eight — evidence: pre-existing `SPEC.md` staleness-count text, not introduced by this story's diff; out of Surface.
  - `[low]` `[defer]` (blind-hunter) R1/R2 lack post-flip expected values (remote URL, foundry project name) — evidence: real operator gap but AC only requires naming checks, not target values; future steward doc can add.
  - `[low]` `[defer]` (blind-hunter) no `_bmad/` readiness row despite Scope listing `_bmad/` per home — evidence: out of original AC's five named facts; Story 44.5 covers estate move separately.
  - `[low]` `[defer]` (blind-hunter) R5 manual `readlink -f` lacks concrete pass predicate — evidence: same class as R1/R2 manual gaps already disclosed in Non-goals.
  - `[low]` `[defer]` (blind-hunter) no ordered attended runbook — evidence: not in AC; steward 44.12 mechanism story owns procedure shape.
  - `[low]` `[defer]` (blind-hunter) relay note does not prescribe a cutover-readiness State-column string — evidence: by design per first-pass Non-goals softening; steward updates companion by its own process.
  - `[low]` `[defer]` (blind-hunter) R4 lists `bmad-loop validate` without naming which sub-check covers `[dev] skill` — evidence: manual `cat .bmad-loop/policy.toml` path already listed; validate is supplementary.
  - `[low]` `[defer]` (blind-hunter) companion lacks dated frontmatter — evidence: generic docs hygiene; not required by AC; sibling companions vary.
  - `[low]` `[defer]` (blind-hunter) no cross-links to `cutover-readiness.md` P16/G10 rows — evidence: relay memlog + architecture pointer suffice for traceability.
  - `[false]` `[reject]` (blind-hunter) marshal `epics.md` Story 31.5 AC still says rendered policy names `bmad-build-auto` — evidence: governing epics AC is stale fleet text; companion doc correctly states `bmad-dev-auto` per CAP-10; fixing epics.md is a separate reconciliation, not this story's Surface.
  - `[false]` `[reject]` (edge-case-hunter, claim) AC requires tear-down-and-recreate reconciliation — evidence: doc deliberately mechanism-agnostic per Reading E; first pass already scoped to flag-flip old-vs-new state; not a defect.
  - `[false]` `[reject]` (edge-case-hunter, claim) AC claims `marshal homes --json` exposes raw marker/symlink/backlink fields — evidence: companion already corrected to `desynced`/`active_project` only (carried from 2026-09-06 triage).
  - `[false]` `[reject]` (edge-case-hunter, claim) AC claims rendered policy should name `bmad-build-auto` — evidence: companion correctly requires `bmad-dev-auto` (carried from 2026-09-06 triage).
  - `[false]` `[reject]` (edge-case-hunter) `active_project` null when both marker and symlink absent yields false pass — evidence: `_evaluate_home` sets `desynced: true` when slug agreement fails; null `active_project` with `desynced: false` is not a reachable pass state for a provisioned home.
  - `[false]` `[reject]` (edge-case-hunter) Tier-3 backlink never provisioned could pass R3 — evidence: missing/absent backlink sets `tier3_reason`, which forces `desynced: true`; R3 requires `desynced: false`.
  - `[false]` `[reject]` (edge-case-hunter) R5 readlink expected target undefined — evidence: same class as deferred R1/R2 manual-gap items; doc already states R5 is manual inspection with no CLI surface today.
  - `[false]` `[reject]` (intent-alignment) AC reconciliation must assert tear-down-and-recreate — evidence: intentional mechanism-agnostic framing matches steward epics 44.12/44.5 flag-flip model.
  - (verification-gap) no findings — docs-only change; all parts non-behavioral per Step 1 screen.

## Design Notes

**Why a new companion doc instead of extending `spec-loop-home-fleet-refresh/SPEC.md` itself:**
that SPEC's own CAP-1 is about STALENESS detection (staying current with `main`), a live,
recurring concern; cutover readiness is a ONE-TIME target-state definition for a future flip —
different lifecycle, different cadence, same directory. Keeping them as sibling files under one
spec avoids inventing a second spec for a single Effort-S docs story while still not conflating
two distinct concerns inside one `SPEC.md`.

**Why the relay goes to `spec-bmad-suite-lifecycle`, not `spec-python-foundry-cutover`:** both are
steward specs and both already show relay-note precedent in this fleet, but `cutover-readiness.md`'s
own header states it is a companion of `spec-bmad-suite-lifecycle` specifically (CAP-9) — that is
the direct governing spec, so the closing relay note belongs there.

## Verification

**Manual checks (no CLI — this is a docs story):**
- The new companion doc exists, is non-empty, and names: (a) every readiness item with its
  proving check and runner: attended/steward-44.12; (b) the DW-CC-2026-09-04-1 reconciliation.
- `spec-loop-home-fleet-refresh/SPEC.md`'s `companions:` list includes the new file; its
  frontmatter still parses as valid YAML after the edit.
- `architecture-bmad-infra.md` § Loop homes gained a short pointer paragraph, no duplication of
  the full readiness content.
- `spec-bmad-suite-lifecycle/.memlog.md` gained a relay note naming this story and the companion
  doc's path; `cutover-readiness.md` itself is byte-for-byte unchanged (confirmed via `git diff`).
- `python -m pyforge.doctor.sources spec-surface` (via `pixi run -e local-recipes
  spec-surface-check`) still reports `ok` -- none of these are code files under any spec's
  `surface:`, so no governance-list edit is needed for this story.

## Auto Run Result

**Summary:** Follow-up `bmad-build-auto` review pass on an already-shipped Story 31.5 (commit
`74f027b5020`). The loop-home cutover-readiness companion doc, architecture pointer, and steward
memlog relay from the first pass were re-reviewed; five doc corrections landed (wrong epics/DW
line citations, undefined expected slug in R3, per-home R6 check grammar, historiographic note
for resolved DW entry). No new deliverables; `cutover-readiness.md` remains untouched.

**Files changed (this follow-up pass only):**
- `loop-home-cutover-readiness.md` — line citations corrected; R3/R6/Reconciling tightened.
- `spec-loop-home-fleet-refresh/.memlog.md` — follow-up correction entry; `updated:` bumped.
- `spec-31-5-loop-home-readiness-is-defined-for-the-cutover-flip.md` — follow-up triage log +
  Auto Run Result write-back.

**Review findings breakdown** (24 findings on follow-up pass; first pass had 16 — see both
`## Review Triage Log` sections):
- **Patched** (5 entries): `high` 2 (wrong Story 44.12 and DW-CC line citations); `medium` 1
  (expected slug undefined); `low` 2 (DW resolved status note; R6 per-home scoping).
- **Deferred** (6 entries, all `low`): nine-vs-eight loop-home count in parent SPEC; R1/R2
  expected values; `_bmad/` row absent; R5 pass predicate; no runbook; relay State-column string;
  R4 validate sub-check; companion frontmatter; cross-links.
- **Rejected** (7 entries, `false`): stale epics.md Story 31.5 AC wording; mechanism-agnostic
  reconciliation (intentional); three carried false claim findings from first pass; two edge-case
  false positives on R3 pass semantics.
- **Verification-gap:** clean (docs-only).

**Follow-up review recommendation: `false`** — follow-up pass; patched counts by verdict: high 2,
medium 1, low 2. No `high` patches remain unaddressed; R6 per-home grammar tightened though not
empirically re-run against a live in-flight home (residual risk unchanged from first pass, now
named explicitly in R6's table row).

**Verification performed:**
- Re-read steward `epics.md:2706-2715` (Story 44.12) and `:2636` (Story 44.5 flip note) before
  accepting citation fixes.
- Re-read steward `deferred-work-ledger.md:2591-2598` before accepting DW cite fix.
- `git diff` against `cutover-readiness.md` — empty (steward-owned file untouched).
- `pixi run -e local-recipes spec-surface-check` — no new drift from this docs-only edit (pre-existing
  unrelated `spec-pyforge-core` drift on branch, not introduced here).

**Residual risks:** R6 still not empirically verified against a live in-flight loop home; the
three first-pass deferred items (audit trail, rollback guidance, test-locked citations) remain
tracked in frontmatter; parent SPEC.md's "9 today" count vs companion's "eight" is unresolved
pre-existing staleness.
