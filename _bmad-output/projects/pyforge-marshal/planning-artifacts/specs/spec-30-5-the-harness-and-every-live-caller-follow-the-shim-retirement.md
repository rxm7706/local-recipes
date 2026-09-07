---
title: "Story 30.5: The harness and every live caller follow the shim retirement"
type: 'feature'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
baseline_revision: 'a67687da5454226cb43cabf3d6fffd2489025c0d'
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** BMAD 6.12 renamed the `bmad-dev-auto` skill to `bmad-build-auto` (a forwarding shim
keeps the old name working through 6.x). Marshal's own `_POLICY_TEMPLATE` in
`harness_bmadloop.py` still vendors `skill = "bmad-dev-auto"` into every loop-home's rendered
`.bmad-loop/policy.toml` — the literal steward's own CAP-9 (`--no-shims`) refusal check already
treats as a live blocker. Several caller sites named in this story's own Surface line have gone
stale in different ways: two cite paths that no longer exist (`.claude/skills/bmad-dev-auto/{step-04-review.md,spec-template.md}`
moved to `bmad-build-auto/`), one has a present-tense docstring citing the retired name as
current behavior, and one already-correctly-glossed guard test deliberately EXCLUDES this exact
literal from its retirement scan — for a reason that flips once the template itself changes.

**Approach:** Rename the template's emitted skill id to `bmad-build-auto` and update its render
test to match. Fix the two dead-path citations (doctor's `chain.py`, marshal's own
`marshal-policy.toml`) to point at the current `bmad-build-auto`/`bmad-build` skill directories.
Rename the one present-tense docstring hit in `cli/spin.py` (and its test mirror) and the one
present-tense line in `docs/dreams/README.md` to lead with the live name. Widen
`test_no_retired_bmad_skill_ids.py`'s `SCAN_GLOBS` to cover the harness template now that its
literal is `bmad-build-auto` (a reintroduced `bmad-dev-auto` there is now genuinely a regression,
not the load-bearing current value the test's own docstring previously excluded it for) — landed
as its OWN CFE-surface-sanctioned `retro:`-prefixed commit with a CHANGELOG.md bump, per this
repo's standing convention, never folded into the marshal-station commit. After the code lands,
the orchestrator (not this story's implementation subagent) re-renders the 8 real
`~/.bmad-loops/pyforge-*/.bmad-loop/policy.toml` files via `marshal config --write-harness-policy`
and confirms `bmad-loop validate` is clean 8/8 — a live, machine-local, idempotent action kept
outside this subagent's scope so it can be run and verified directly.

## Boundaries & Constraints

**Always:**
- Only touch files this story's own Surface line names (see Code Map) — a fuller repo sweep
  found many more `bmad-dev-auto` hits in Dreams, decks, `docs/specs/`, and `pixi.toml`, but those
  are either already correctly historical-glossed, out of this story's declared surface, or
  explicitly-shipped history that must never be rewritten. Leave all of them untouched.
- Where a hit is present-tense guidance describing CURRENT behavior, rename to lead with
  `bmad-build-auto`, mirroring this repo's own already-established gloss convention (see
  `.claude/skills/bmad-loop-setup/SKILL.md:58`: "`bmad-build-auto` (the upstream dev primitive;
  `bmad-dev-auto` on pre-rename releases)") — do not invent new phrasing.
- Where a hit cites a file path, verify the path is CURRENT (not just rename the skill id in
  prose) — two of this story's named sites cite a now-dead `bmad-dev-auto/<file>.md` path; fix
  the path itself, not just the words around it.
- The `test_no_retired_bmad_skill_ids.py` change is its own commit, subject `retro: ...`, with a
  `.claude/skills/conda-forge-expert/CHANGELOG.md` PATCH-bump entry (8.86.4 -> 8.86.5) in the SAME
  commit — do not fold it into any other commit (CFE-surface convention, enforced by
  `mason_cfe_surface_check`).

**Never:**
- Do not touch `_bmad/**` (installer-owned, regenerated) or `.claude/skills/bmad-dev-auto/SKILL.md`
  (the shim's own identity file — it must keep saying `bmad-dev-auto`, that is its whole job).
- Do not touch any `pyforge-steward` source or test file — `upgrade.py`'s CAP-9 detector and its
  test fixtures deliberately construct `bmad-dev-auto`-shaped synthetic data to prove the detector
  catches it; none of that is stale documentation, all of it is intentional and version-independent.
- Do not touch decks (`presentations/**`), `docs/specs/**`, `pixi.toml` comments, `docs/dreams/*.md`
  (other than `README.md`'s one named line), or any archived/shipped-history file — glossed-never-
  rewritten, and most are already out of this story's own declared surface.
- Do not re-render the 8 real loop-home `policy.toml` files or run `bmad-loop validate` as part of
  the dispatched implementation work — that is a live, machine-local action the orchestrator
  performs directly after this code change is verified, not part of the subagent's job.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Template render | `render_policy_toml()` after the change | `[dev]` section emits `skill = "bmad-build-auto"` | N/A |
| Render test | `test_harness_policy_render.py` | Asserts `doc["dev"]["skill"] == "bmad-build-auto"` | A stale assertion would red, catching a future revert |
| Retired-ID guard widened | `test_no_retired_bmad_skill_ids.py` after the change | `SCAN_GLOBS` includes the harness template path; a planted `bmad-dev-auto` there reds the suite | The guard's docstring rationale is updated to match (no longer "load-bearing", now guarded like everything else) |
| Dead path fixed (doctor) | `chain.py`'s comment citing `bmad-dev-auto/step-04-review.md` | Comment cites `bmad-build-auto/step-04-review.md` (the file that actually exists there today) | N/A |
| Dead path fixed (marshal-policy.toml) | Lines 27-28 citing two now-dead skill dirs | Cites `bmad-build-auto/spec-template.md` / `bmad-build/spec-template.md` (both confirmed to exist) | N/A |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py:328` —
  `_POLICY_TEMPLATE`'s `[dev]` section: `skill = "bmad-dev-auto"` -> `skill = "bmad-build-auto"`.
  This is the ONLY `bmad-dev-auto` occurrence anywhere in this file (confirmed by full-file
  search) — no other docstring/comment in this file needs touching.
- `src/shared/packages/pyforge-marshal/tests/unit/test_harness_policy_render.py:90` —
  `assert doc["dev"]["skill"] == "bmad-dev-auto"` -> `assert doc["dev"]["skill"] == "bmad-build-auto"`.
  Do not touch the surrounding untouched-stock-defaults assertions on lines 86-89/91.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` (around lines 767-770) —
  docstring reads: `"...but every spec ``bmad-dev-auto`` actually writes carries a descriptive
  title after the key..."`. Reword to name the live skill: `"...but every spec
  ``bmad-build-auto`` actually writes carries a descriptive title after the key..."`. Check
  `src/shared/packages/pyforge-marshal/tests/unit/test_spin.py` around lines 1159-1160 and
  1168-1170 for an identical mirrored docstring/comment string — if it is prose commentary (not
  an assertion against `spin.py`'s literal docstring text), update it the same way for
  consistency; if it is an actual string-equality assertion against the real docstring, update
  both together so the test still passes.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` (around lines
  2336-2339) — comment reads: `` "Ports `.claude/skills/bmad-dev-auto/step-04-review.md`'s
  \"Minting the id\" prose..." ``. The file has moved; fix the path to
  `` `.claude/skills/bmad-build-auto/step-04-review.md` `` (verify this exact path exists before
  committing to it). Leave the rest of the comment (the historical "Story 8.2" framing) unchanged
  — only the path is dead, not the provenance narrative.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml:27-28` — comment
  reads:
  ```
  # frontmatter (`.claude/skills/bmad-dev-auto/spec-template.md` /
  # `.claude/skills/bmad-quick-dev/spec-template.md`) -- authored, never derived from
  ```
  Both cited paths are dead. Replace with the current locations (verify both exist first):
  ```
  # frontmatter (`.claude/skills/bmad-build-auto/spec-template.md` /
  # `.claude/skills/bmad-build/spec-template.md`) -- authored, never derived from
  ```
- `docs/dreams/README.md` (around line 32) — reads: `"...then drives the code with the **BMAD
  Method** — bmad skills + phases run autonomously via **bmad-loop** and **bmad-dev-auto**."`.
  Reword to lead with the live name: `"...via **bmad-loop** and **bmad-build-auto**."` (a light
  gloss such as "(bmad-dev-auto pre-6.12)" is optional here since the sentence is a short current-
  state summary, not documentation someone will hunt a file path from — use judgment, but do not
  invent a "retired 2026-09" phrasing not already used elsewhere in this repo).
- `.claude/skills/conda-forge-expert/tests/meta/test_no_retired_bmad_skill_ids.py` — **SEPARATE
  COMMIT, subject `retro: ...`:**
  - `SCAN_GLOB_FLOORS` dict (around lines 135-140): add one new entry for the harness template,
    e.g. `"src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py": 0`
    (floor 0 — there should be zero retired-id hits in it after this story's own rename; the
    floor exists so the file must still be scannable, not that it must contain a minimum count of
    anything). Verify the exact `SCAN_GLOB_FLOORS` dict shape by reading the live file first — the
    floor semantics (what a "floor" means for a single non-glob file vs. a `**/*` glob) must match
    how existing single-file entries (e.g. `"AGENTS.md": 1`, `"CLAUDE.md": 1"`) are interpreted;
    do not guess the wrong shape.
  - Module docstring (around lines 49-54): currently argues this exact literal is excluded from
    scanning because it "is Spec-mandated to survive... that literal is load-bearing, not a stale
    instruction." Update this rationale to reflect the new state: the harness template's `[dev]
    skill` value is now `bmad-build-auto` (the live default), so the retired-ID scan now covers it
    like any other surface — a reintroduced `bmad-dev-auto` there would be a genuine regression,
    not the current load-bearing value. Keep the docstring's explanation of *why* it existed
    historically (so a future reader understands the reasoning changed, not that it was wrong).
  - `.claude/skills/conda-forge-expert/CHANGELOG.md` — add a new PATCH entry, `v8.86.5`, dated
    2026-09-06, one-paragraph summary in the same style as the existing `v8.86.4` entry (see that
    entry for the "fleet-hygiene retro... landed via pyforge-marshal Story 30.X" phrasing
    convention) — this story's version: widened `SCAN_GLOBS` to cover the harness template now
    that its `[dev] skill` literal is `bmad-build-auto`, landed via `pyforge-marshal` Story 30.5
    (spec-bmad-611-era-alignment CAP-12). No recipe, gotcha, or Operating-Principle change.
  - `.claude/skills/conda-forge-expert/SKILL.md` — bump `version: 8.86.4` -> `version: 8.86.5` in
    frontmatter, and add the one-line "what's new" bullet to its own version-history section if
    one exists near the top (mirror however `v8.86.4` was recorded there).
  - Any other file the `v8.86.4` bump touched for version bookkeeping (e.g.
    `config/skill-config.yaml`, `MANIFEST.yaml` — check the v8.86.4 CHANGELOG entry's own "Files"
    list for the exact set) — bump identically for `v8.86.5`.

## Tasks & Acceptance

**Execution:**
- `harness_bmadloop.py` -- rename the template's `[dev] skill` literal -- the core CAP-12 change.
- `test_harness_policy_render.py` -- update the matching assertion -- keeps the render test honest.
- `cli/spin.py` (+ `test_spin.py` if it mirrors the string) -- rename the present-tense docstring
  reference -- stops citing a retired name as current behavior.
- `chain.py`, `marshal-policy.toml` -- fix the two dead-path citations -- both currently point at
  files that no longer exist.
- `docs/dreams/README.md` -- rename the present-tense flow-diagram line -- same reasoning.
- `test_no_retired_bmad_skill_ids.py` + CHANGELOG.md + SKILL.md (+ its version-bookkeeping
  siblings) -- widen `SCAN_GLOBS`, update the docstring rationale, and record a PATCH retro --
  **as one separate `retro:`-prefixed commit**, per the CFE-surface convention.

**Acceptance Criteria:**
- Given `render_policy_toml()` runs after this change, when the rendered `[dev]` section is read,
  then `skill == "bmad-build-auto"`.
- Given `pixi run -e pyforge-marshal pyforge-marshal-test`, when run after this story, then it is
  green.
- Given a planted `skill = "bmad-dev-auto"` string temporarily written into
  `harness_bmadloop.py` (a manual check, not a permanent test fixture), when
  `test_no_retired_bmad_skill_ids.py` runs, then it reds — proving the widened `SCAN_GLOBS`
  actually covers the file (revert the plant immediately after checking).
- Given the two dead-path citations, when the paths they now cite are checked with `ls`, then
  both resolve to real files.
- Given `pixi run -e local-recipes test-skill --keyword test_no_retired_bmad_skill_ids`, when run
  after the SCAN_GLOBS change, then it passes.

## Spec Change Log

### 2026-09-06 — bad_spec finding: the story's central premise is false
**Triggering finding:** during implementation, the dispatched engineer attempted the
`harness_bmadloop.py` rename (`skill = "bmad-dev-auto"` -> `"bmad-build-auto"`) and hit a
`PolicyError` from the installed `bmad_loop` 0.11.1 package. Independently re-verified by the
orchestrator by reading `bmad_loop/policy.py` directly: `DevPolicy.skill` is a **permanent
internal adapter discriminator** (`DEV_SKILLS = {"bmad-dev-auto"}`, hard-validated), not a
"which skill name is current" field. The actually-invoked skill name is resolved separately at
runtime (`Engine._dev_skill()` / `install.dev_primitive_or_default`); upstream's own comment:
"a project on either era works with this field untouched." Renaming the literal would throw on
every real loop-home's policy load — `bmad-loop validate` would fail 8/8, not pass 8/8.

**What was amended:** the Code Map's harness-rename bullet, the render-test bullet, and the
`test_no_retired_bmad_skill_ids.py` SCAN_GLOBS-widening bullet (+ its dependent `retro:` commit)
are now understood to describe work that must NOT happen — the `<intent-contract>` text is left
unmodified (it is read-only per this exact story's own bad_spec routing rule) as the historical
record of what was originally asked and why it was wrong; this Spec Change Log entry is the
correction layer. The surviving, independently-true parts of the original Approach (the two
dead-path citation fixes, the two present-tense docstring/prose renames) are unaffected and were
implemented and verified normally.

**Known-bad state avoided:** force-completing the harness rename to satisfy the story's literal
AC would have broken every one of the 8 real loop-homes' `bmad-loop validate`, and would have
made steward Story 14.9's CAP-9 refusal pass on a corrupted premise rather than a fixed one.

**KEEP:** the two dead-path-citation fixes and the two present-tense-docstring renames are
correct, independently justified, and verified — they must survive any future re-derivation of
this story's remaining (harness-side) scope.

## Review Triage Log

### 2026-09-06 — Review pass (Blind Hunter, Edge Case Hunter, Verification Gap Reviewer, Intent Alignment Auditor)
- verdicts: 10 findings — high 0, medium 0, low 3, false 7, maybe-false 0 (of the 3 low, 1 patched and 2 rejected as out-of-scope)
- findings:
  - `[false]` `[reject]` Blind Hunter: `harness_bmadloop.py:328` still reads `bmad-dev-auto`, unmet per the story's own AC — verified true as a mechanical fact, but refuted as a defect: this is the exact, independently-verified bad_spec finding above (the rename would break the installed `bmad_loop` package's own validated contract); intentionally not done.
  - `[false]` `[reject]` Blind Hunter: doc/behavior "mismatch" — `marshal-policy.toml`/`chain.py` now cite `bmad-build-auto` while the adapter still renders `bmad-dev-auto` — refuted: these two facts are unrelated and both true simultaneously. The cited files are FILE-SYSTEM PATHS (the skill's `SKILL.md`/`spec-template.md` really do live under `.claude/skills/bmad-build-auto/` today, verified), not claims about the internal `DevPolicy.skill` discriminator value. No contradiction.
  - `[false]` `[reject]` Blind Hunter: `test_harness_policy_render.py:90` still asserts `bmad-dev-auto`, "unmet" per the story's AC — same refutation as the first row; the assertion is correct as-is and must stay.
  - `[false]` `[reject]` Blind Hunter: `test_no_retired_bmad_skill_ids.py`'s `SCAN_GLOBS` was not widened — same refutation; the widening's own rationale ("a reintroduced `bmad-dev-auto` there is now genuinely a regression") never becomes true, since the literal must stay `bmad-dev-auto` permanently.
  - `[low]` `[reject]` Blind Hunter: `pyforge-warden/__init__.py:8` has a bare, ungossed `bmad-quick-dev` mention — verified true, but out of scope: `bmad-quick-dev` (-> `bmad-build`) is a DIFFERENT skill rename than this story's CAP-12 target (`bmad-dev-auto` -> `bmad-build-auto`); the story's own Intent/Approach never names `bmad-quick-dev`.
  - `[low]` `[reject]` Blind Hunter: `core/promotion.py`, `core/status.py`, `cli/deploy.py` contain bare `bmad-quick-dev` mentions, inconsistent with `cli/spin.py` (which was fixed) — verified true, but out of scope for the same reason: those are all `bmad-quick-dev` hits (a different rename target), while `spin.py`'s fix was specifically a `bmad-dev-auto` hit, correctly in this story's scope.
  - `[low]` `[patch]` Blind Hunter: `docs/dreams/README.md` itself has two more bare mentions nearby (lines ~200, ~207) the diff didn't touch, leaving the file internally inconsistent — verified true for BOTH. Line 200 ("`bmad-dev-auto` writes bare `- source_spec:` bullets") names the SAME retirement target (`bmad-dev-auto`) as a present-tense claim about which skill currently writes deferred-work entries — in scope, and genuinely inconsistent with the fix two lines above it in the same file. **Fixed:** renamed to `bmad-build-auto`. Line 207 ("hand-implemented via `bmad-quick-dev`") is the DIFFERENT `bmad-quick-dev` rename target — out of scope, left untouched (same reasoning as the two rows above).
  - `[false]` `[reject]` Blind Hunter: the story's Surface citation for the README line ("`docs/dreams/README.md:30`") doesn't match the actual edit site (~32) — verified true as a mechanical fact, but refuted as a defect: story Surface line-number citations drifting from the actual file is an already-established, accepted pattern in this repo (e.g. Story 30.3's CLAUDE.md citations were similarly stale) — not something this diff needs to correct.
  - `[false]` `[reject]` Blind Hunter: the diff includes no embedded verification evidence (test reruns, `bmad-loop validate` output) — refuted: verification evidence for a diff-review pass lives in the review record (this triage log + the orchestrator's own command runs below), not embedded inside the diff itself, which is a content artifact, not an execution log (same established refutation as prior stories this session).
  - `[false]` `[reject]` Edge Case Hunter + Verification Gap Reviewer (independent, same finding): the spec's Intent/Approach/Tasks&Acceptance claim the harness template and its render test were changed, but they were not — verified true as a textual fact, but this is the bad_spec finding itself, already fully explained in the Spec Change Log above and in this triage's first three rows; not a new, unexplained defect.

## Design Notes

**Why this story's actual footprint is much smaller than its own Surface line implies.** A
repo-wide investigation (not just the named sites) found that several of this story's own listed
callers require NO CHANGE: `CLAUDE.md`'s two real hits (lines 119 and 135, not the stale
119/126/135-137/201 the story names) already correctly gloss `bmad-dev-auto` as the dated
pre-6.11 name; `pyforge-warden/__init__.py` has zero hits at all (nothing there today mentions
`bmad-dev-auto`); `promotion.py`/`status.py`/`cli/deploy.py` either don't exist at the paths named
or have zero hits; `seed/templates/manifest.yaml`'s two hits are already correctly glossed. This
spec only lists the sites that actually need a change, confirmed by direct inspection — do not
"complete" the story's originally-named list by touching files that turned out to need nothing.

**Why the live loop-home re-render and `bmad-project-context` pitfall note are explicitly NOT in
this spec's scope.** The re-render of the 8 real `~/.bmad-loops/pyforge-*/.bmad-loop/policy.toml`
files is a live, machine-local, outside-the-repo mutation this story's own AC calls for — but it
belongs to the orchestrator running it directly and verifying `bmad-loop validate` afterward, not
a dispatched code-implementation subagent (mirrors the same code-vs-live-action split already
applied to steward Story 14.9 in this same session). The `bmad-project-context` pitfall note is
explicitly gated on "after the apply lands" (the steward `--no-shims` apply, Session 2 step 9) —
this story only prepares the ground for that apply to succeed; it does not run after it.

## Verification

**Commands:**
- `cd src/shared/packages/pyforge-marshal && pixi run -e pyforge-marshal pytest tests/unit/test_harness_policy_render.py tests/unit/test_spin.py -q` -- expected: all pass.
- `cd src/shared/packages/pyforge-marshal && pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: green.
- `pixi run -e local-recipes test-skill --keyword test_no_retired_bmad_skill_ids` -- expected: green.
- `pixi run -e local-recipes detectors-ci` -- expected: clean or unchanged pre-existing findings only (in particular `mason_cfe_surface_check` must stay clean once the CFE-surface change lands as its own `retro:`-prefixed commit).

## Auto Run Result

**Summary:** This story's central premise — renaming `harness_bmadloop.py`'s vendored `[dev]
skill = "bmad-dev-auto"` literal to `"bmad-build-auto"` — was found FALSE during implementation
and independently re-verified by the orchestrator against the installed `bmad_loop` 0.11.1
package's own source: `DevPolicy.skill` is a permanent internal adapter discriminator that must
stay `"bmad-dev-auto"` forever (hard-validated, `PolicyError` on any other value); the actually-
invoked skill name is resolved separately at runtime, independent of this field. Renaming it
would break `bmad-loop validate` on all 8 real loop-homes, not fix anything. Consequently the
harness rename, its render-test update, and the `test_no_retired_bmad_skill_ids.py` SCAN_GLOBS
widening (+ its dependent CFE-surface `retro:` commit) were never applied. Only the parts of this
story's own scope that are independently true regardless of that false premise were implemented:
two dead file-path citations (pointing at skill directories that really did move under the 6.12
rename) and three present-tense docstring/prose renames (a fourth was added during review: one
more `bmad-dev-auto` mention inside `docs/dreams/README.md` itself, found by the review pass).

**This exposes a real, unresolved defect in steward's already-landed Story 14.9 (CAP-9):**
`_shim_retirement_blockers`'s naive text-match against `harness_bmadloop.py` for this exact
literal will refuse `--no-shims` FOREVER, since the literal can never legitimately change to
satisfy it. Session 2 step 9 (the live `--no-shims` apply) cannot succeed as currently designed
until CAP-9 is taught to exempt this specific permanent literal — a fix that belongs in
`pyforge-steward`, explicitly out of this story's own Never-boundary and out of this session's
approved plan. Reported to the operator; not fixed here.

**Files changed:**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` — two dead-path citations fixed.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` — one dead-path citation fixed.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` — one present-tense docstring rename.
- `src/shared/packages/pyforge-marshal/tests/unit/test_spin.py` — the same rename mirrored (docstring prose, no assertion change).
- `docs/dreams/README.md` — two present-tense line renames (one from the initial pass, one from the review pass).
- 7 foreign-spec memlogs (`spec-pixi-candidate-currency`, `spec-pyforge-doctor`, `spec-adaptive-model-tiering`, `spec-bmad-loop-liveness-footgun`, `spec-marshal-parallel-dispatch-fanout`, `spec-marshal-single-story-dispatch`, `spec-pyforge-marshal`) — reconcile notes.
- `scripts/.spec-surface-baseline.json` — re-stamped scoped for all 7.

**NOT changed (deliberately, per the bad_spec finding):** `harness_bmadloop.py`, `test_harness_policy_render.py`, `test_no_retired_bmad_skill_ids.py`, `.claude/skills/conda-forge-expert/{CHANGELOG.md,SKILL.md}`.

**Review findings breakdown:** 10 findings — 1 patched (low), 2 rejected as out-of-scope (low,
wrong skill-rename target: `bmad-quick-dev` is not this story's CAP-12 concern), 7 rejected as
false (all either the already-explained bad_spec finding itself, or refuted on independent
verification).

**Follow-up review recommendation:** `false` — only 1 low-verdict patch this pass, well under
the 2+ medium threshold.

**Verification performed:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` — 7510 passed, 12 deselected.
- `pixi run -e pyforge-doctor pyforge-doctor-test` — 1341 passed, 1 skipped.
- `pixi run -e local-recipes test-skill --keyword test_no_retired_bmad_skill_ids` — 9 passed (file untouched, as intended).
- Both dead-path citations confirmed to resolve to real files via direct `ls`.
- `bmad_loop/policy.py` read directly to independently confirm the bad_spec finding (not just trusting the implementation subagent's report).
- `pixi run -e local-recipes python -m pyforge.doctor.sources spec-surface` — clean after reconcile + scoped re-stamp of 7 foreign specs.
- `pixi run -e local-recipes detectors-ci` — 17/18 clean (pre-existing `dream-chain` finding only, marshal-owned, unrelated); `mason_cfe_surface_check` clean (no CFE-surface file touched, as intended).

**Residual risks / blocking condition:** this story is marked `blocked`, not `done` — its stated
intent (CAP-12, the harness rename + guard widening) cannot be completed as specified. The
5-file valid subset is real, verified progress and is being committed and pushed. The actual
blocker — steward CAP-9's false-positive refusal on a permanent literal — needs a NEW story or a
correction to spec-bmad-611-era-alignment/spec-bmad-suite-lifecycle (owner's decision), scoped to
`pyforge-steward`, before Session 2 step 9 (the live `--no-shims` apply) can succeed.

**Resolution (2026-09-06, same session):** operator decided "spec correction." `spec-bmad-611-era-alignment`
CAP-12, `spec-bmad-method-core-upgrade` CAP-9, and `spec-bmad-suite-lifecycle` CAP-10 are all
corrected in place (dated correction notes, `<intent-contract>`-equivalent text left as historical
record where those specs use that convention). Steward Story 14.9's own false refusal check
(`_shim_retirement_blockers` / `refuse_shim_retirement_not_ready`, plus the `--loops-home` flag
that only existed to parameterize it) is removed in the same session, via a follow-up
`bmad-build-auto` review pass on its own spec, mirroring this story's own review discipline.
With that fix, this story's ENTIRE real scope (the caller-site glosses; the harness template is
permanently, not temporarily, out of scope) is complete. Status flips `blocked` -> `done`; no
further work remains for Story 30.5.
