---
title: 'Loop-home readiness is defined for the cutover flip'
type: 'chore'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
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

**Summary:** Wrote the loop-home cutover-readiness definition steward 44.12 needs (G10/P16 of
`spec-bmad-suite-lifecycle`'s `cutover-readiness.md`): a new companion doc under
`spec-loop-home-fleet-refresh/` naming six readiness facts (R1-R6), the existing check that
proves each, and the runner (steward 44.12, attended per P16). Relayed to steward via a memlog
note rather than hand-editing `cutover-readiness.md` directly (steward-owned, out of Surface).
Reconciled `DW-CC-2026-09-04-1`'s "retired" wording with P16's "re-provisioned" wording. The
first implementation pass contained three real factual errors caught by independent review —
two claims (R3, R4) that didn't match live code, and one (the Scope section's description of
steward 44.12's mechanism) that didn't match the actual story text — all corrected and
independently re-verified in this pass.

**Files changed:**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh/loop-home-cutover-readiness.md`
  (new) — the readiness definition; R3/R4/Scope/Reconciling/Non-goals corrected during review.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh/SPEC.md`
  — `companions:` gains the new file.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-loop-home-fleet-refresh/.memlog.md`
  — event entry (companion doc added) + correction entry (review-pass fixes); `updated:` bumped.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md` — short
  pointer paragraph in § Loop homes.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md`
  — relay note (cross-project, in-scope per this story's own Surface line); `updated:` bumped.
  `cutover-readiness.md` itself confirmed byte-for-byte unchanged throughout.

**Review findings breakdown** (16 findings across blind-hunter, edge-case-hunter,
verification-gap [clean], intent-alignment; full evidence in `## Review Triage Log`):
- **Patched** (6 entries): `high` — R4's claim that the rendered policy should name
  `bmad-build-auto` was already-known-false (verified live against the actual rendered
  `policy.toml` and the installed `bmad_loop` package's hard-validated `DEV_SKILLS`; the
  correction was already sitting in the very memlog file this diff touches); `high` — the Scope
  section's "tears down and rebuilds" description of steward 44.12 didn't match that story's
  actual `pyforge.cutover_root` flag-flip definition (verified by reading `epics.md` verbatim);
  `high` — R3 cited internal `HomeFacts` field names that `marshal homes --json` never actually
  serializes (verified by reading `_evaluate_home`'s real row dict); `medium` — the "memlog is
  the single writer" claim for `cutover-readiness.md`'s State column overstated a convention
  P4 scopes to `SPEC.md` only (softened to an honest "gives steward what it needs" framing);
  `medium` — both memlog appends left `updated:` frontmatter stale (bumped, matching
  `memlog.py::touch()`'s own convention); `low` — the `DW-CC-2026-09-04-1` paraphrase implied
  the whole ledger entry was about loop homes when it's one line-item in a 268-worktree
  aggregate (scoped explicitly).
- **Deferred** (3 entries, in this spec's frontmatter `deferred:`, all `low`): no audit trail
  (sign-off log) for the three manual-only readiness items; no failure/rollback guidance for the
  attended eight-times-repeated procedure; the doc's field-name citations against live code
  aren't wired to any test.
- **Rejected** (4 entries, `false`): `SPEC.md`'s `companions:` edited directly rather than via
  `bmad-spec` re-derive (refuted by extensive established precedent in this exact spec family,
  including Story 31.4 one story prior in this same batch); the check-surface split (some items
  manual, not all landing on the AC's named pair) — matches the story's own Type=docs/Effort=S
  signal and is transparently disclosed, not a hidden gap; `cutover-readiness.md` left unedited —
  by design, per the story's own Surface line; the FR/AD grounding being indirect — expected for
  any decomposition of a high-level architecture decision.

**Follow-up review recommendation: `true`** — this pass patched three `high`-verdict entries.
Patched-entry counts by verdict: high 3, medium 2, low 1. Unverified risk to name per the rule:
R6's citation of `marshal status` / `bmad-loop status` as the per-home "no run in flight" check
was not empirically re-run against a live in-flight home in this pass (no run was in progress to
test against during review) — it rests on established fleet convention (team practice: check
`bmad-loop status <run_id> --json` + `list --json`) rather than a fresh, this-story-specific
confirmation that either command cleanly scopes to one loop-home's state the way R6 implies.

**Verification performed:**
- Independently confirmed `~/.bmad-loops/pyforge-marshal/.bmad-loop/policy.toml:66` reads
  `skill = "bmad-dev-auto"` and the installed `bmad_loop` package's `policy.py:44` hard-validates
  `DEV_SKILLS = {"bmad-dev-auto"}` (before accepting the R4 fix).
- Independently read `core/status.py::_evaluate_home`'s actual row-dict construction and
  confirmed it emits only `path`, `branch`, `slug`, `active_project`, `desynced` (before
  accepting the R3 fix).
- Independently read `epics.md` Story 44.12 (lines 2685-2693) and Story 44.5's flip note (line
  2619) verbatim (before accepting the Scope-section fix).
- `pixi run -e local-recipes spec-surface-check` — `ok`, re-run after both implementation
  rounds.
- `python3 -c "yaml.safe_load(...)"` — `SPEC.md` frontmatter and both memlogs' frontmatter parse
  as valid YAML with the expected fields (`companions`, bumped `updated:`), re-run after the
  fix round.
- `git diff --stat` against `cutover-readiness.md` — empty, confirmed twice (before and after
  the fix round) that the steward-owned file was never touched.
- `git diff --stat` against `baseline_revision` — touches exactly the 5 intended files after
  both rounds, nothing stray.

**Residual risks:** the R6 risk named above; the three deferred items (audit trail, rollback
guidance, test-locked field citations) are real, tracked in this spec's frontmatter, and
explicitly out of this Effort-S/docs story's scope; the Reconciling section's honest
"unclear from epics.md" framing for whether the flip's own tooling already satisfies R3-R5 means
steward 44.12's eventual implementation may still need its own judgment call here — this doc
deliberately does not resolve that ambiguity on steward's behalf.
