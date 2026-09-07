---
title: 'Release comms go through bmad-os-changelog and -social'
type: 'feature'
created: '2026-09-07'
status: 'done'
baseline_revision: '32d0971b961c32ab2453fc00a6cb87f6ec711b40'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<!-- Note: this spec was written directly to the tracked `planning-artifacts/specs/` home
     (rather than staged first in the gitignored Tier-3 `implementation-artifacts/`) because
     this dev session runs in a worktree whose `implementation-artifacts` symlink resolves
     outside the worktree; the sandbox's worktree-isolation guard correctly refuses a write
     there. Landing directly in the durable location is the same end state the normal
     "promote after merge" convention reaches anyway. -->

<intent-contract>

## Intent

**Problem:** `bmad-agent-herald/SKILL.md`'s AD-2 routing section for `bmad-os-changelog` /
`bmad-os-changelog-social` is a bare one-line "wields" mention (added incidentally by steward
46.2 to satisfy its own generic AD-2 meta-test) — it does not describe how a bmad-suite
release's comms actually flow through the two skills into an operational record, which is
CAP-3's actual routing-note contract and this story's own Given/When/Then ("routes release
notes to `bmad-os-changelog` and the social variant to `bmad-os-changelog-social` feeding
`herald notice`").

**Approach:** Expand that section into a concrete, followable procedure (producer-artifact
check → changelog draft → social draft → `herald notice`/`herald success` filing), and add a
herald-local meta-test that machine-checks it — including the AD-10 "check against the
producer's live artifact" this story's own acceptance criteria require.

## Boundaries & Constraints

**Always:**
- The routing note's only durable home stays `.claude/skills/bmad-agent-herald/SKILL.md`
  (AD-2); `AGENTS.md`'s existing single pointer line and `CLAUDE.md` (untouched, already true)
  are left exactly as they are.
- The new procedure text documents who does what; it does not add persona CLI code. FR-13
  grammar stays `pyforge herald …` (unchanged).
- Frame the two utility skills (`bmad-os-changelog`, `bmad-os-changelog-social`) as ordinary
  Claude Code skills invoked by whoever does the suite's release work — **not** part of the
  Herald persona's own CAP-16 action set (they write files directly; CAP-16's Forbidden
  actions rule that out for the persona transcript itself). Only the final filing step
  (`pyforge herald notice …` / `pyforge herald success …`) is a persona `grammar` action.
- Before routing to either skill, the documented procedure checks the producer's live artifact
  (AD-10b): `.claude/skills/bmad-os-changelog/` and `.claude/skills/bmad-os-changelog-social/`
  both exist (they do, live, via steward 46.2).
- New test lives at `src/shared/packages/pyforge-herald/tests/meta/test_release_comms_routing.py`
  so `pyforge-herald-test` alone proves this story's AC without depending on
  `pyforge-steward`'s own generic AD-2 suite.

**Never:**
- Do not create a `CHANGELOG.md` at the repo root or fabricate a live "next suite refresh" run
  to literally execute the skills — the compiled epic context (Epic 18, 2026-09-07) explicitly
  scopes both this story and 18.3 as "a routing-note change only." The G/W/T's "one release …
  has its note produced through them" clause is satisfied structurally, by the procedure text
  being concrete and correct, matching CAP-3's own Success bar (routing table + persona
  citation + meta-test — no live-fire requirement).
- Do not edit `adoption-register.md` (§ 2 row 34 already names herald sole wielder for both
  skills and cites `bmad-agent-herald` as the durable home — verified accurate, read-only) or
  `release-cadence.md` (steward-owned surface, AD-11) — reference both, edit neither.
- Do not touch the `## Allowed actions (CAP-16)` / `## Forbidden actions` headings or the
  "Lane 1 CMS stays steward" sentence in the persona `SKILL.md` — `tests/meta/test_skf_skill_
  and_persona.py` pins their exact shape.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Both producer skills present (today's live state) | `.claude/skills/bmad-os-changelog/` and `-social/` both exist | New meta-test's producer-check passes | No error expected |
| A producer skill regresses away later | one of the two dirs is deleted in a future change | `test_producer_skills_are_live_on_disk` fails, naming the missing dir | AssertionError names the exact missing path (AD-10 catch) |

</intent-contract>

## Code Map

- `.claude/skills/bmad-agent-herald/SKILL.md` -- lines 12-14 today: the one-line AD-2 mention to
  expand into the numbered procedure. Leave `## Allowed actions (CAP-16)` / `## Forbidden
  actions` / the "Lane 1 CMS stays steward" line untouched (pinned by
  `tests/meta/test_skf_skill_and_persona.py::test_live_persona_skill_forbids_filesystem_and_
  adhoc_http` and `::test_does_not_implement_wave_b_or_cms`).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` -- read-only ground truth for
  the CLI shape cited in the new prose: `notice author --type {deprecation,fix,eol} --component
  --what --why --migration --deadline --reason-link --publish` (`NOTICE_TYPES =
  ("deprecation","fix","eol")`, line ~615), `success create <project_name> --evidence-notice
  <component> ...` (line ~484).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/
  adoption-register.md` § 2 (row: `bmad-os-changelog, bmad-os-changelog-social | utility-skills
  | herald | ...`) -- read-only reference; already correct, not edited.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/
  release-cadence.md` step 7 ("Mason — suite refresh") -- read-only cross-reference: the trigger
  event the new procedure responds to; file itself is steward-owned (AD-11), not edited.
- `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py` -- read-only
  reference: `test_skill_routing_matches_ad2_for_every_currently_provisioned_row` already proves
  AD-2 generically for these two skills off the existing one-line mention; the new herald-local
  test must not duplicate it, only add herald-specific procedure + AD-10 assertions.
- New: `src/shared/packages/pyforge-herald/tests/meta/test_release_comms_routing.py`.

## Tasks & Acceptance

**Execution:**
- `.claude/skills/bmad-agent-herald/SKILL.md` -- replace the "Utility skill routing (AD-2)"
  section's single sentence with a short numbered procedure: (0) note both skills are ordinary
  Claude Code skills invoked by whoever does the release work, not part of this persona's own
  CAP-16 action set; (1) AD-10 producer check — confirm `.claude/skills/bmad-os-changelog/` and
  `.claude/skills/bmad-os-changelog-social/` both exist before routing; (2) draft the refresh's
  CHANGELOG entry with `bmad-os-changelog`; (3) draft the social posts with
  `bmad-os-changelog-social` from that same entry; (4) file the operational record via FR-13
  grammar — a deprecation/fix/eol-shaped line becomes `pyforge herald notice author --type
  <deprecation|fix|eol> --component <name> --what … --why …` (`--publish` once reviewed); a
  plain capability-shipped line becomes `pyforge herald success create "<project>"
  --evidence-notice <component>` instead. -- fulfills CAP-3's routing-note contract beyond the
  bare "wields" mention; grounds the abstract G/W/T in the CLI's real flags so the procedure is
  followable, not aspirational.
- `src/shared/packages/pyforge-herald/tests/meta/test_release_comms_routing.py` (new) -- assert:
  (a) both producer skill `SKILL.md` files exist on disk (AD-10 machine check); (b) the persona
  `SKILL.md`'s routing section mentions `bmad-os-changelog`, `bmad-os-changelog-social`,
  `herald notice`, `herald success`, and cites `AD-10`; (c) it names both producer skill
  directories literally; (d) `adoption-register.md`'s combined changelog/social row still names
  `herald`; (e) `CLAUDE.md` never mentions `bmad-os-changelog`. -- makes the story's G/W/T
  machine-checkable from `pyforge-herald-test` alone; (a)+(c) together are the AD-10 producer
  check this story's acceptance requires.

**Acceptance Criteria:**
- Given the two skills installed live (steward 46.2), when `pyforge-herald-test` runs the new
  meta-test module, then every assertion passes and no file outside herald's own surface
  (`.claude/skills/bmad-agent-herald/**`, the new test file) is touched.
- Given the persona `SKILL.md`'s AD-2 section, when read literally, then it describes a
  concrete, numbered release-comms procedure ending in `herald notice`/`herald success` — not
  merely a "wields" mention.
- Given `adoption-register.md` § 2 and `CLAUDE.md`, when inspected after this story, then the
  register still names herald as sole wielder for both skills (unchanged) and `CLAUDE.md`
  mentions neither (unchanged).
- Given `tests/meta/test_skf_skill_and_persona.py` (Story 17.1's CAP-16 gate) and
  `pyforge-steward`'s `test_adoption_register.py` (Story 46.1's AD-2 gate), when both suites run
  after this story's edit, then both stay green — the new prose neither disturbs the pinned
  Allowed/Forbidden headings nor removes the backtick-quoted skill names steward's test scans
  for.

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 11 findings — high 0, medium 0, low 8, false 3, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind Hunter: spec frontmatter `status: 'in-review'` conflicts with the same-pass ledger flip to `done` — refuted: this step's own Finalize section writes `status: done` into the spec before HALT; the reviewed diff was staged mid-pass, between the "set in-review" instruction and Finalize, so the mismatch is resolved by this same workflow step, not a residual defect.
  - `[low]` `[reject]` Blind Hunter: spec frontmatter has no `updated:` field, unlike sibling done specs (`spec-17-1-...`, `spec-17-2-...`) — true, but the fix is to edit this build's spec (frontmatter hygiene only, no code/behavior consequence); rejected per the "fix is to edit this build's spec" rule.
  - `[low]` `[reject]` Blind Hunter: spec frontmatter `context: []` despite relying on `epics.md`/`SPEC.md`/`adoption-register.md` — true, same rejection ground as above (spec-only fix).
  - `[low]` `[reject]` Blind Hunter: Code Map cites `NOTICE_TYPES` at cli.py:615, but it's defined in `notices.py:106` (cli.py:615 is a use site) — verified true; spec-only citation-accuracy fix, rejected per the "fix is to edit this build's spec" rule.
  - `[low]` `[reject]` Blind Hunter: Code Map cites "line ~484" for `--evidence-notice`, but the flag itself is added at cli.py:519 (484 is the subparser's own instantiation) — verified true; same rejection ground (spec-only).
  - `[false]` `[reject]` Blind Hunter: the Never section's quoted phrase "a routing-note change only" does not appear in `epics.md`/`epics-with-stories.md` — refuted: the spec attributes the quote to "the compiled epic context" (`epic-18-context.md`), not `epics.md`; that file contains the phrase verbatim (soft-wrapped across two lines) at its own lines 34-35. The reviewer checked the wrong source.
  - `[low]` `[patch]` Blind Hunter: the numbered release-comms procedure in `SKILL.md`'s AD-2 section starts at "0." folding a framing caveat into the same sequence as steps 1-4, risking a reader mistaking "0." for an executable step — fixed: moved the caveat into a lead-in sentence before the list; the list now starts at 1 and still names both skills, `herald notice`, `herald success`, and `AD-10` (all pinned tokens preserved; `pyforge-herald-test` reconfirmed green, 1248 passed).
  - `[low]` `[patch]` Blind Hunter: no tracked artifact records why this story stops at documentation rather than a live release run, for a future reader — fixed via a shipped-code path instead of editing the spec: added a paragraph to `test_release_comms_routing.py`'s module docstring citing the durable sources (`spec-bmad-suite-lifecycle` CAP-3 Success criteria, AD-2) instead of relying solely on the ephemeral, gitignored `epic-18-context.md` cache.
  - `[low]` `[patch]` Edge Case Hunter: `test_producer_check_would_fail_and_name_a_missing_producer_dir`'s `present_dir, absent_dir = PRODUCER_SKILL_DIRS` 2-tuple unpack would raise `ValueError` (masking the intended AD-10 assertion) if `PRODUCER_SKILL_DIRS` ever grows past two entries — fixed: rewritten as `*present_dirs, absent_dir = PRODUCER_SKILL_DIRS` with an explicit `len(...) >= 2` precondition assertion, so the test degrades gracefully instead of crashing on an arity change.
  - `[low]` `[reject]` Edge Case Hunter: the spec's Acceptance Criteria says "no file outside herald's own surface... is touched," but the diff also touches the new spec file and the ledger flip — true as a reading of that AC bullet, but the fix is to reword spec prose (no shipped-code consequence); rejected per the "fix is to edit this build's spec" rule.
  - `[false]` `[reject]` Intent Alignment Auditor: reported the diff implements a documentation-only reading (B/C) while the story's recoverable intent language ("one release... has its note produced through them") points to live execution (Reading A), and that the resolution rests on an out-of-diff artifact — refuted on the merits: `spec-bmad-suite-lifecycle/SPEC.md`'s own CAP-3 "Success" criterion (routing table + persona citation + meta-test) does not require a live-fire run, and `ARCHITECTURE-SPINE.md` AD-2 defines the routing note's durable home as the persona skill, not a live release execution — both are durable, tracked, independently-checkable sources (not the ephemeral compiled-context cache alone), so Reading B/C is the intended, evidenced scope rather than an under-delivery.

## Design Notes

The CAP-16 tension is real and worth naming: `bmad-os-changelog` writes `CHANGELOG.md` directly
and `bmad-os-changelog-social` writes `.social/**` directly, but the Herald persona's own
Forbidden actions rule out direct filesystem writes in its transcript. The resolution (already
implicit in how every other § 2 row works — e.g. doctor wielding `bmad-os-root-cause-analysis`)
is that "wielding" is an organizational/routing fact, not a claim that the CAP-16-gated persona
conversation itself performs the write. The new SKILL.md prose says this explicitly so a future
reader (or reviewer) doesn't mistake the routing note for a persona capability grant.

## Verification

**Commands:**
- `pixi run -e pyforge-herald pyforge-herald-test` -- expected: full suite green, including the
  new `tests/meta/test_release_comms_routing.py`.
- `pixi run -e pyforge-steward pyforge-steward-test -k test_adoption_register` -- expected:
  stays green (confirms the SKILL.md edit didn't remove the backtick-quoted names steward's own
  AD-2 test scans for).

## Auto Run Result

**Summary:** Expanded `bmad-agent-herald/SKILL.md`'s AD-2 "Utility skill routing" section from a
one-line "wields" mention into a concrete, numbered release-comms procedure (producer-artifact
check → changelog draft → social draft → `herald notice`/`herald success` filing), and added a
herald-local meta-test proving that procedure and the AD-10 producer check. Both the register's
naming of herald as sole wielder and `CLAUDE.md`'s silence on the two skills were verified
unchanged. Flipped `18-2-release-comms-go-through-bmad-os-changelog-and-social` from `blocked`
to `done` in `sprint-status-ledger.yaml` (same-commit convention per steward Story 46.2's own
precedent).

**Files changed:**
- `.claude/skills/bmad-agent-herald/SKILL.md` -- AD-2 section rewritten as a followable procedure.
- `src/shared/packages/pyforge-herald/tests/meta/test_release_comms_routing.py` (new) -- 7 tests
  machine-checking the routing text, the AD-10 producer check (live + synthetic negative case),
  the register row, and `CLAUDE.md`'s silence.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml` -- `18-2-...`
  flipped `blocked` → `done`.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-18-2-....md` (this file, new).

**Review findings breakdown:** 11 findings across 4 layers (Blind Hunter 8, Edge Case Hunter 2,
Verification Gap 0, Intent Alignment 1). 3 patched (all `low`, all in shipped files, not the
spec): the SKILL.md numbered-list caveat placement, the test module's docstring durability note,
and a fragile 2-tuple unpack in the new synthetic test. 3 `false` (refuted with cited evidence --
see Review Triage Log above). 5 rejected under the "fix is to edit this build's spec" rule (spec
frontmatter hygiene: `updated:` field, `context:` list, two Code Map line-citation
imprecisions, and one AC-wording nit) -- all verified true as spec-prose observations, none with
a code-level fix available, none affecting the shipped deliverable's correctness. 0 deferred.

**Follow-up review recommendation:** `false`. All 3 patched entries were `low` severity (no
`high`, fewer than two `medium`).

**Verification performed:** `pixi run -e pyforge-herald pyforge-herald-test` -- 1248 passed, 4
skipped (re-run after patches). `pixi run -e pyforge-steward pyforge-steward-test -k
test_adoption_register` -- 6 passed (re-run after patches). Diff staged and read independently
of the implementation subagent's own report at each stage; Matrix Test Audit closed a real gap
(added `test_producer_check_would_fail_and_name_a_missing_producer_dir` so both I/O matrix rows
are covered by a passing test, not just the happy path).

**Residual risks:** None rising to `medium`+. The rejected spec-hygiene findings (missing
`updated:` field, empty `context:` list, two imprecise Code Map line citations) remain true of
this spec file but carry no functional consequence -- noted here rather than silently dropped.
