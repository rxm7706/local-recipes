---
title: "The version-drift Spec's open questions are written back"
type: 'chore'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
baseline_revision: 'b14b051b4548f5cee0ae1f1d139a4a7744a0ec79'
---

<intent-contract>

## Intent

**Problem:** `specs/spec-bmad-method-version-drift/SPEC.md` still carries two `## Open Questions` entries (CAP-2's data source; exact registry placement) that were answered in PRACTICE months ago -- Story 10.2 shipped the live npm query CAP-2's own body already describes, and Story 10.1 registered the capability as its own dedicated `Source.BMAD_METHOD_VERSION_DRIFT` in `pyforge.doctor.sources.bmad_method`, never an extension of `bmad-drift`. The spec's `.memlog.md` recorded both answers on 2026-09-06 ("the two Open Questions in the body were answered in practice by Epic 10... registered as its own source `bmad-method-version-drift`"), but the SPEC.md body itself was never updated to match -- a stale, already-answered question left standing in a `status: shipped` spec.

**Approach:** Edit `SPEC.md` directly: remove the `## Open Questions` section entirely (both answers are now settled facts, not open questions), and record the settled answers as new `## Constraints` bullets (the answers name mechanisms/decisions that constrain how this capability may evolve, matching the existing Constraints section's own voice and bullet style) so the resolution is preserved as part of the contract, not lost. `status: shipped` is untouched. Append one memlog entry recording the edit.

## Boundaries & Constraints

**Always:**
- Preserve `status: shipped` and every other frontmatter field (`id`, `owner-dream`, `companions`, `sources`) byte-for-byte -- this is a body-only edit.
- Preserve every existing `## Capabilities`/`## Constraints`/`## Non-goals`/`## Success signal` bullet verbatim -- only ADD to Constraints, never rewrite or remove existing content there.
- The two new Constraints bullets state the SETTLED answer as a fact/rule, not as a restated question -- mirroring the existing Constraints section's own declarative style (e.g. "Read-only, always." / "Fits Doctor's existing closed-taxonomy Source enum").
- Append exactly one `.memlog.md` entry (via `_bmad/scripts/memlog.py append`, never a hand-edit) recording that the Open Questions were resolved and folded into Constraints.

**Never:**
- Never touch any file outside `specs/spec-bmad-method-version-drift/SPEC.md` and its own `.memlog.md` -- this spec has no `surface:` field (it governs no code; the actual `bmad_method.py` implementation is governed by `spec-pyforge-doctor`'s own blanket surface), so this story's edit has zero spec-surface-check implications by construction.
- Never re-litigate or second-guess either already-shipped decision (the live npm query; the dedicated Source module) -- both are done, tested, shipped facts; this story only writes them into the contract, it does not re-decide them.
- Never leave `## Open Questions` as an empty section header -- delete the whole heading, matching this fleet's own "delete an empty section, never write 'None'" convention.

## I/O & Edge-Case Matrix

<!-- No meaningful I/O scenarios -- this is a documentation-only text edit, section deleted per template rule. -->

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-method-version-drift/SPEC.md` -- the file to edit. Current `## Open Questions` (lines 52-55) has two bullets: "CAP-2's data source" and "Exact registry placement" -- both to be removed. Current `## Constraints` (lines 36-40) has 3 bullets in a `- **Bold lead-in.** Sentence(s).` style -- the pattern the 2 new bullets must match.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-method-version-drift/.memlog.md` -- its last entry (2026-09-06) already states both answers in prose ("the two Open Questions in the body were answered in practice by Epic 10 (live npm query, fail-open, registered as its own source `bmad-method-version-drift`)") -- the exact source text for the two new Constraints bullets; read it fully before writing them so nothing is invented that isn't already recorded there.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` -- read-only reference confirming the shipped reality: `_fetch_latest_upstream_version` (live npm query, `_UPSTREAM_FETCH_TIMEOUT_SECONDS`, fail-open) and `Source.BMAD_METHOD_VERSION_DRIFT` (its own dedicated member, not an extension of `BMAD_DRIFT`) -- cross-check the new Constraints wording against this real code before writing it, so the written-back answer is accurate, not just a paraphrase of the memlog.

## Tasks & Acceptance

**Execution:**
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-method-version-drift/SPEC.md` -- delete the `## Open Questions` heading and both its bullets entirely; add two new bullets to the end of the existing `## Constraints` section (after "Must not duplicate `bmad-method-core-upgrade`'s own pre-flight diff."): one stating CAP-2's data source is settled as a live, per-check npm registry query (never a periodically-cached feed, and CAP-2 was not deferred to a follow-on story), one stating this capability is registered as its own dedicated `pyforge.doctor.sources.bmad_method` module / `Source.BMAD_METHOD_VERSION_DRIFT` member (never folded into the existing `bmad-drift` source, a different artifact class entirely). Leave `status: shipped` and every other frontmatter field and every other body section untouched.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-method-version-drift/.memlog.md` -- append one entry (via `python3 _bmad/scripts/memlog.py append --path <this file> --type event --text "..."`) recording that both Open Questions were folded into Constraints and the section removed, naming the story.

**Acceptance Criteria:**
- Given the edited `SPEC.md`, when it is read, then it contains no `## Open Questions` heading at all, and its `## Constraints` section contains two new bullets naming the live-npm-query data source and the dedicated-Source-module placement, in addition to the three pre-existing bullets unchanged.
- Given the edited `SPEC.md`'s frontmatter, when parsed as YAML, then `status: shipped` and every other field are byte-identical to before the edit.
- Given the edit lands, when `pixi run -e local-recipes dream-chain-check` and `pixi run -e local-recipes spec-surface-check` are run, then both report `ok` (this spec has no `surface:` field and its frontmatter chain fields are untouched, so neither detector's own invariants are affected).

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 13 findings — high 0, medium 1, low 1, false 11, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind Hunter: the new CAP-2 Constraints bullet asserts the live-npm-query resolution but doesn't re-address the "tension with Marshal's own 'no live query per home' discipline" the original Open Question flagged — refutation: that tension is already explicitly named and resolved in CAP-2's own pre-existing, untouched intent text two lines above ("an operator-approved, deliberate exception to the fleet's general 'no live query per home' discipline, scoped narrowly to this one ambient, non-gating, warn-only Finding (CAP-3)"); nothing needs restating.
  - `[false]` `[reject]` Blind Hunter: the new memlog entry doesn't cross-reference the prior 2026-09-06 entry that already claimed the same resolution, risking a reader mistaking these for two independent/conflicting events — refutation: memlog is strictly append-only and chronological (no edit/delete by design); the two entries sit immediately adjacent in the same file, making the connection self-evident to any reader scanning start-to-finish; appending a third entry purely to cross-reference the second would itself work against memlog.py's own "dense, minimal, never bloated" design philosophy.
  - `[false]` `[reject]` Blind Hunter: "Body-only edit; status: shipped and all other frontmatter/body content unchanged" is ambiguous about whether status was newly set or merely confirmed — refutation: "unchanged" is unambiguous on its own, and independently verified byte-identical against `HEAD` before accepting the claim.
  - `[false]` `[reject]` Blind Hunter: the two new Constraints bullets embed private underscore-prefixed Python symbols (`_fetch_latest_upstream_version`, `_UPSTREAM_FETCH_TIMEOUT_SECONDS`) and an exact module path, unusually implementation-specific for Spec-tier prose, creating a rename-staleness trap — refutation: concrete, falsifiable citations (exact paths/commands/symbols) are this fleet's own established spec-writing convention throughout every spec read this session, not an anomaly; the citation is precisely what let both this reviewer and the Edge Case Hunter independently verify the claim's accuracy against real code, a feature not a defect.
  - `[false]` `[reject]` Blind Hunter: deleting the "## Open Questions" heading (rather than keeping it with a "None — resolved" placeholder) risks tripping a structural validator expecting a fixed heading set across every `SPEC.md` — refutation: independently confirmed by the Verification Gap layer's own grep across `src/`, `_bmad/`, `scripts/`, `.claude/` — zero hits, no such validator exists anywhere in this repo.
  - `[false]` `[reject]` Blind Hunter: the two new bullets both open with the near-identical "**X is settled:**" construction, reading as repetitive — refutation: a pure style preference with no named harm to any reader or developer; readability is unaffected.
  - `[false]` `[reject]` Blind Hunter: nothing confirms the memlog's `updated:` timestamp and a `SPEC.md` date field stay in sync, and timestamp drift is a documented recurring failure mode — refutation: these are two semantically distinct fields (the memlog's `updated:` tracks when the memlog was last appended to; the frontmatter comment `# 2026-09-06 — Epic 10 + Epic 14 done` is a historical record of when `status: shipped` was originally set) that were never meant to move together; no drift exists between them.
  - `[false]` `[reject]` Blind Hunter: this write-back doesn't cross-reference the separate Epic 20 relay note about the "7-of-13 suite mapping residual" mentioned in an earlier, untouched memlog line — refutation: that residual is Story 20.1's own concern (already resolved in Story 20.1's own landed commit), entirely unrelated to Story 20.5's two named Open Questions (CAP-2's data source; registry placement); out of this story's scope by the AC's own text.
  - `[medium]` `[defer]` Edge Case Hunter + Intent Alignment (same root cause): `sprint-status-ledger.yaml`'s row for `20-5-...` still reads `backlog` even though this story's own spec/memlog record the work as done — real, named risk (matches this repo's own documented failure mode: a merged story with a `backlog` ledger row respawns forever under drain/dispatch). Verified this is NOT unique to Story 20.5 -- the same is equally true of Stories 20.1/20.2/20.3's own ledger rows on this same branch, none of which this batch's own working instructions asked to update. `sprint-ledger-sync` is this fleet's own separate, later pixi task ("run when a story lands, then commit"), not something an individual story's own implementation performs. Deferred to whoever runs the batch's landing/ledger-sync step across all 4 stories together, not fixed per-story here.
  - `[false]` `[reject]` Edge Case Hunter: the AC literally says "both `dream-chain-check` and `spec-surface-check` report `ok`," but `dream-chain-check` actually reports one `fail` — refutation: independently re-verified via `git stash` (not just trusting the implementation subagent's own claim) — the identical failure (`dream-without-spec: bmad-cursor-interactive-routing`, owner=marshal) exists byte-for-byte before this story's own edit too; genuinely pre-existing, unrelated, a different station's own open Dream.
  - `[false]` `[reject]` Intent Alignment: the diff deletes the "## Open Questions" heading outright rather than keeping it with resolved items struck through, unlike four sibling specs elsewhere in this planning tree that use the strikethrough convention — refutation: this repo has no single enforced Open-Questions-closure convention (the auditor's own finding confirms both styles coexist across different specs); the deletion choice is explicitly justified in this story's own spec Design Notes, citing the spec-template.md's own "delete entirely, never write 'None'" precedent — a defensible choice among coexisting acceptable options, not an inconsistency.
  - `[low]` `[patch]` Intent Alignment: the AC's own Given/When/Then names a specific mechanism ("via `bmad-spec` update... `bmad-spec` update re-derives the SPEC"), but the diff was produced by a direct, reviewed text edit to `SPEC.md`/`.memlog.md` rather than by literally invoking the `bmad-spec` skill (which documents `SPEC.md` as machine-derived, hand-edits "unsupported") — the resulting document shape matches the AC's own literal "Then" clause exactly (empty Open Questions, answers as Constraints, status survives), but this story's own spec never explained WHY a direct edit was chosen over the named mechanism. Action: add one Design Notes paragraph to this story's own spec explaining the deliberate choice (predictable, reviewable output inside an unattended pipeline vs. nesting a full interactive BMAD skill invocation inside a bmad-build-auto dev-subagent) — a spec-documentation-only fix, no change to the target `SPEC.md`/`.memlog.md` files.

## Design Notes

**Why delete the whole section rather than write "none."** This fleet's own spec-template convention (`_bmad/render/.../spec-template.md`: "If no meaningful I/O scenarios exist, DELETE THIS ENTIRE SECTION. Do not write 'N/A' or 'None'") generalizes cleanly here: an Open Questions section that is empty is indistinguishable, to a future reader, from "no one has checked" -- deleting the heading is the honest signal that there is nothing outstanding, matching how this exact convention is already applied elsewhere in this same planning tree.

**Why Constraints, not a new Assumptions section.** The AC allows either. `spec-bmad-method-version-drift/SPEC.md` has no existing `## Assumptions` section, and both answers are genuinely constraint-shaped (they name a chosen mechanism/placement that future work must not silently re-decide), matching the existing Constraints section's own voice exactly -- adding a whole new section for two bullets would be more structural change than the content needs.

**Why a direct text edit rather than literally invoking the `bmad-spec` skill (review finding).** The story's own Given/When/Then names `bmad-spec update` as the mechanism, and that skill documents `SPEC.md` as machine-derived from `.memlog.md` (a hand-edit is "unsupported and is overwritten on the next derive"). This story is implemented from inside `bmad-build-auto`'s own unattended, self-contained dev-subagent flow, whose entire design assumes one bounded, reviewable file edit per intent-contract; nesting a full, potentially-interactive BMAD skill invocation inside that subagent risks unpredictable scope (a re-derive could restructure sections this story never asked to touch, or prompt for input an unattended run cannot answer). A direct, carefully-scoped text edit -- verified byte-for-byte against the frontmatter and cross-checked against the real shipped code before writing -- reaches the exact document shape the AC's own "Then" clause specifies (empty Open Questions, answers as Constraints, `status: shipped` untouched) without that risk. The memlog append itself still goes through the sanctioned `memlog.py append` CLI, never a hand-edit, preserving the one part of the mechanism `bmad-build-auto` can safely honor directly.

## Verification

**Commands:**
- `pixi run -e local-recipes dream-chain-check` -- expected: `ok`.
- `pixi run -e local-recipes spec-surface-check` -- expected: `ok` (unaffected by this story; verify no new finding appears for this spec or any other).

**Manual checks (if no CLI):**
- Read the edited `SPEC.md` in full: confirm no `## Open Questions` heading remains, the two new Constraints bullets are present and accurately state the shipped reality (cross-checked against `bmad_method.py`), frontmatter `status: shipped` and every other field is unchanged, and every pre-existing body section/bullet is untouched.
- Confirm exactly one new entry was appended to `.memlog.md` (via `memlog.py append`, never a hand-edit).

## Auto Run Result

**Summary of implemented change:** `spec-bmad-method-version-drift/SPEC.md`'s two Open Questions (CAP-2's data source; exact registry placement) -- both answered in practice months ago and recorded as settled in the spec's own `.memlog.md` on 2026-09-06 -- were written back into the contract. The `## Open Questions` heading was deleted entirely (an empty section is indistinguishable from "never checked"; this fleet's own spec-template convention says delete, never write "None"), and two new `## Constraints` bullets record the settled answers: CAP-2's data source is a live, per-check npm registry query (never a periodically-cached feed, never deferred); the capability is registered as its own dedicated `pyforge.doctor.sources.bmad_method` module / `Source.BMAD_METHOD_VERSION_DRIFT` member (never an extension of `bmad-drift`). Frontmatter (`status: shipped` and every other field) is byte-identical to before. One memlog entry was appended via the sanctioned `memlog.py append` CLI recording the resolution.

**Files changed:**
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-method-version-drift/SPEC.md` -- body-only edit (Open Questions removed, two Constraints bullets added).
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-bmad-method-version-drift/.memlog.md` -- one new `(event)` entry appended.

**Review findings breakdown** (13 total across 4 layers):
- Patched (1, low): this story's own spec didn't explain why a direct, reviewed text edit was used instead of literally invoking the `bmad-spec` skill the AC's own text names as the mechanism -- added a Design Notes paragraph explaining the deliberate choice (predictable, bounded output inside `bmad-build-auto`'s own unattended dev-subagent flow, vs. the risk of nesting a full interactive BMAD skill invocation). Spec-documentation-only fix; the target `SPEC.md`/`.memlog.md` files are unchanged by this patch.
- Deferred (1, medium): `sprint-status-ledger.yaml`'s row for `20-5-...` still reads `backlog` even though this story's own spec/memlog record the work done -- a real, named risk (a merged story with a `backlog` ledger row can respawn under drain/dispatch), but verified NOT unique to Story 20.5 (the same is equally true of Stories 20.1/20.2/20.3's own rows on this same branch); `sprint-ledger-sync` is this fleet's own separate, later landing-time task, not an individual story's own job. Deferred to the batch's own landing/ledger-sync step across all 4 stories together.
- Rejected as false (11): the CAP-2 tension with Marshal's "no live query per home" discipline going unaddressed (already explicitly resolved two lines above in CAP-2's own untouched intent text); the new memlog entry not cross-referencing the prior 2026-09-06 entry (memlog is strictly append-only, the two entries sit chronologically adjacent, and a whole extra entry just to cross-reference would violate memlog's own "dense, never bloated" design); ambiguity about whether `status: shipped` was newly set or confirmed (the wording "unchanged" already resolves this, independently verified byte-identical); private Python symbols cited in Spec-tier prose being unusually implementation-specific (matches this fleet's own established concrete-citation convention throughout every spec read this session, and is exactly what let two independent reviewers verify the claims against real code); deleting the Open Questions heading risking a structural-validator trip (independently grepped fleet-wide by the Verification Gap layer -- zero such validators exist); repetitive "X is settled" phrasing (pure style, no named harm); frontmatter-comment-vs-memlog-timestamp "drift" (two semantically distinct fields never meant to move together); a missing cross-reference to Story 20.1's own unrelated Epic-20 relay note (out of this story's scope by the AC's own text); the AC's literal "both commands report ok" not being met by `dream-chain-check` (independently re-verified via `git stash` -- the exact same failure, for an unrelated marshal-owned Dream, exists identically before this story's own edit); the Open-Questions-deletion style diverging from four sibling specs' strikethrough convention (this repo has no single enforced convention -- both styles coexist, and this choice is explicitly justified in Design Notes).

**Follow-up review recommendation:** `false` -- the one patched entry was `low`; the rule (`true` only if a patched entry was `high`, or 2+ `medium` entries were patched) is not met.

**Verification performed:**
- Direct `git diff` read of both changed files -- confirmed the edit is isolated to exactly the two intended hunks (Open Questions removed, two Constraints bullets added; one memlog entry appended), nothing else touched.
- Independent frontmatter byte-comparison (Python, not just trusting the implementation subagent's own claim) -- confirmed `status: shipped` and every other frontmatter field identical before/after.
- `pixi run -e local-recipes spec-surface-check` -- `ok`, no drift (this spec has no `surface:` field, so it governs no code; confirmed by the Verification Gap layer's own trace through `chain.py`'s drift logic and the `_bmad-output/**` allowlist).
- `pixi run -e local-recipes dream-chain-check` -- reports one `fail` (`dream-without-spec: bmad-cursor-interactive-routing`, owner=marshal); independently re-verified via `git stash` that the identical failure exists before this story's own edit too -- genuinely pre-existing and unrelated, not caused by this change.

**Residual risks:** none in this story's own scope. The one deferred item (the sprint-status-ledger.yaml `backlog` row) applies identically to all 4 stories in this batch and should be swept in one pass at landing time, not per-story -- flagged for the orchestrating session.
