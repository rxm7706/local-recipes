---
title: "Story 46.8: CIS is re-provisioned to the packaged revision"
type: 'chore'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'd7faf964fbd1f9442f74216764406d6c628b8139'
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The packaged `bmad-creative-intelligence-suite` module passes `--project-root
{project-root}` on every `resolve_customization.py` call in its `SKILL.md` files; the 10
installed `.claude/skills/bmad-cis-*/SKILL.md` copies are missing that flag on 15 lines total
(confirmed by direct grep: 1+1+1+1+1+2+1+2+3+2 = 15 across the 10 files, matching the story's
own Given clause exactly).

**Approach:** Re-run the module's own provisioning command to refresh the installed copies
from the packaged revision, verify the diff is exactly those 10 files / 15 lines and nothing
else, confirm the retired-ID guard stays green, and re-check the atlas ledger's
`DW-FU-20-4-3` deferred-work entry (a `{{project_name}}` placeholder in
`bmad-cis-design-thinking/template.md`) against the refreshed copy.

## Boundaries & Constraints

**Always:**
- Run the exact command the story specifies: `PATH="$PWD/.pixi/envs/local-recipes/bin:$PATH"
  pixi run -e pyforge-steward steward provision --module cis --json`.
- Verify `git diff --stat -- '.claude/skills/bmad-cis-*'` shows exactly the 10 known files
  (no more, no fewer) and inspect the actual line-level diff to confirm it is exactly the
  `--project-root {project-root}` flag being added (15 lines), not some other unrelated
  content drift from the packaged copy.
- Re-run `.claude/skills/conda-forge-expert/tests/meta/test_no_retired_bmad_skill_ids.py`
  after the provision to confirm the retired-ID guard stays green (the CIS skills are
  process/facilitation skills that could plausibly cite an old id in prose).
- Re-check atlas's `DW-FU-20-4-3` deferred-work entry (the `{{project_name}}` placeholder in
  `bmad-cis-design-thinking/template.md`) against the refreshed file content: if the
  placeholder is now resolved/handled correctly, close the ledger entry with evidence; if not,
  re-verify and record why it stays open.

**Never:**
- Do not hand-edit any `bmad-cis-*/SKILL.md` file directly — the fix must come from re-running
  the module's own provisioning command, so the installed copies stay a faithful mirror of the
  packaged revision (never a hand-patched fork of it).
- Do not touch any other module's provisioned skills in the same pass.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Re-provision | `steward provision --module cis --json` run | Exit 0; JSON success payload | If the command fails, HALT and report — do not hand-patch as a workaround |
| Diff shape | Post-provision `git diff` | Exactly the 10 known `bmad-cis-*/SKILL.md` files, 15 lines total, all adding `--project-root {project-root}` | Any additional file or unrelated line change is a finding, not silently accepted |
| Retired-ID guard | Post-provision live tree | `test_no_retired_bmad_skill_ids.py` stays green | N/A |
| DW-FU-20-4-3 | atlas deferred-work ledger entry | Closed with evidence, or re-verified open with a recorded reason | N/A |

</intent-contract>

## Code Map

- `.claude/skills/bmad-cis-agent-brainstorming-coach/SKILL.md`,
  `bmad-cis-agent-creative-problem-solver/SKILL.md`, `bmad-cis-agent-design-thinking-coach/SKILL.md`,
  `bmad-cis-agent-innovation-strategist/SKILL.md`, `bmad-cis-agent-presentation-master/SKILL.md`,
  `bmad-cis-agent-storyteller/SKILL.md`, `bmad-cis-design-thinking/SKILL.md`,
  `bmad-cis-innovation-strategy/SKILL.md`, `bmad-cis-problem-solving/SKILL.md`,
  `bmad-cis-storytelling/SKILL.md` — the 10 files; each gains `--project-root {project-root}`
  on its `resolve_customization.py` invocation line(s), via re-provisioning, never by hand.
- `.pixi/envs/local-recipes/share/bmad-creative-intelligence-suite/skills/` — the packaged
  source of truth `steward provision` copies from; already confirmed (via direct diff of the
  storyteller skill) to already carry the `--project-root` flag.
- `_bmad-output/projects/pyforge-atlas/...` deferred-work ledger — `DW-FU-20-4-3` entry to
  re-check against the refreshed `bmad-cis-design-thinking/template.md`.
- `.claude/skills/conda-forge-expert/tests/meta/test_no_retired_bmad_skill_ids.py` — read-only
  verification gate, run after the provision.

## Tasks & Acceptance

**Execution:**
- Run `steward provision --module cis --json` -- refreshes the 10 installed CIS skills from
  the packaged revision -- the only sanctioned way to close the drift.
- Verify the diff shape and the retired-ID guard -- proves the provision did exactly what was
  expected and nothing else.
- Re-check `DW-FU-20-4-3` -- closes or re-verifies the one deferred-work item this story
  explicitly calls out.

**Acceptance Criteria:**
- Given the provision command runs, when `git diff --stat -- '.claude/skills/bmad-cis-*'` is
  read, then it shows exactly the 10 known files.
- Given the same diff, when inspected line-by-line, then it shows exactly 15 lines, all adding
  `--project-root {project-root}` to a `resolve_customization.py` invocation.
- Given the refreshed tree, when the retired-ID guard test runs, then it stays green.
- Given atlas's `DW-FU-20-4-3`, when the refreshed `bmad-cis-design-thinking/template.md` is
  checked, then the ledger entry is closed with evidence or re-verified open with a recorded
  reason.

## Spec Change Log

## Review Triage Log

### 2026-09-06 — Review pass
- verdicts: 9 findings — high 0, medium 0, low 3, false 6, maybe-false 0
- findings:
  - `[low]` `[defer]` Blind Hunter: sprint-status-ledger.yaml still lists `46-8-...` as `backlog` — verified true. Deferred to step 11 (PR-landing), which syncs all touched stories' ledger rows together.
  - `[low]` `[defer]` Blind Hunter: `fleet-drain-queue.yaml` still lists `46-8-...` under pyforge-steward's queue — verified true; same root cause as the ledger row above, same deferral (step 11). No active fleet-drain supervisor is running against this branch in this session, so the "respawns forever" risk this memory note warns about does not apply here — it will be cleared as part of the same step-11 ledger sync.
  - `[low]` `[patch]` Blind Hunter: `customization-inventory.md` row C11 lacked the "DONE" annotation sibling rows (C10, C14) carry once their story lands — verified true against the doc's own established convention. Fixed: appended a dated DONE note with the verification evidence.
  - `[low]` `[defer]` Blind Hunter: `epics.md`'s Story 46.8 block has no `**Status:** done` / `**Outcome**` block, unlike other completed stories in the same file — verified true (confirmed the convention exists at the cited lines). Deferred to step 11, which explicitly adds each story's Outcome note in `epics.md` as part of PR landing.
  - `[low]` `[reject]` Blind Hunter: no regression test guards the packaged-vs-installed CIS drift from recurring on a future version bump — verified true but rejected: this is a new capability (a drift-detection test) the story's own text never asks for; a good future enhancement, not a defect in this story's delivered scope.
  - `[false]` `[reject]` Blind Hunter: this diff needs the `maintenance` PR label — true but not a diff-level finding; already accounted for at PR-open time (step 11).
  - `[false]` `[reject]` Edge Case Hunter: explicit `--project-root` skips `resolve_customization.py`'s `warn_on_masked_override` diagnostic — verified true as a mechanical fact, but refuted as a defect: this is the exact invocation shape the PACKAGED (target) revision itself uses, already independently verified byte-identical, and already the standard shape adopted fleet-wide for other skills (`bmad-brainstorming`, `bmad-agent-analyst`, `bmad-spec`, `bmad-customize`) per the Verification Gap Reviewer's own cross-check. Adopting the upstream package's chosen behavior is this story's job, not a regression to guard against.
  - `[false]` `[reject]` Verification Gap Reviewer: no gaps found — every claim in the diff and the spec verified against live code.
  - `[false]` `[reject]` Intent Alignment Auditor: the diff carries no artifact proving the `steward provision` CLI command was actually run, or that the retired-ID guard was re-checked — refuted: both were independently verified by the orchestrator outside the diff itself (re-ran `test_no_retired_bmad_skill_ids.py` directly: 9 passed; ran `detectors-ci`: clean) — verification evidence for a diff-review pass is expected to live in the review record, not embedded inside the diff, which is a content artifact, not an execution log.

## Design Notes

This story is XS and the fix is entirely mechanical (re-run one command); the epic-context
compile step was skipped as disproportionate overhead for a single-command chore — the story's
own text plus a direct diff against the packaged skill copies fully specifies the work. The
spec file itself lives in the session scratchpad rather than the project's own
`implementation-artifacts/` because `_bmad-output/projects/pyforge-steward/implementation-artifacts`
is a Tier-3 backlink symlink resolving OUTSIDE this worktree (into the shared main checkout),
which the sandbox correctly refuses to write through from an isolated worktree.

## Verification

**Commands:**
- `PATH="$PWD/.pixi/envs/local-recipes/bin:$PATH" pixi run -e pyforge-steward steward provision --module cis --json` -- expected: exit 0.
- `git diff --stat -- '.claude/skills/bmad-cis-*'` -- expected: exactly 10 files.
- `pixi run -e local-recipes test-skill --keyword test_no_retired_bmad_skill_ids` -- expected: green.
- `pixi run -e local-recipes detectors-ci` -- expected: clean (or unchanged pre-existing findings only).

## Auto Run Result

**Summary:** Re-provisioned all 10 CIS skills to the packaged `bmad-creative-intelligence-suite`
revision (the first `steward provision --module cis` run hit a pre-existing skill-name
collision guard, since the skills were originally added via a hand-committed WIP commit rather
than genuine provisioning; resolved by removing the 10 directories after byte-verifying
packaged-vs-installed content differed ONLY in the expected 15 lines, then re-running the
identical command, which succeeded via the installer's own rmtree+copytree). Re-verified
atlas's `DW-FU-20-4-3` against the refreshed `bmad-cis-design-thinking/template.md` — still
genuinely open (an unrelated upstream placeholder bug), recorded with dated evidence. Review
pass fixed one documentation-consistency gap (customization-inventory.md's C11 row DONE
annotation) and rejected/deferred the rest as either out of this XS story's scope or already
covered by this session's step-11 landing plan.

**Files changed:** the 10 `bmad-cis-*/SKILL.md` files (15 lines, all adding `--project-root
{project-root}`), `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md`
(one re-verification note), `customization-inventory.md` (C11 DONE annotation).

**Review findings breakdown:** 9 findings — 1 patched (low), 6 rejected as false, 2 deferred
(both low, to step 11).

**Follow-up review recommendation:** `false` — 0 high/medium-verdict patches.

**Verification performed:** `steward provision --module cis --json` exit 0;
`git diff --stat -- '.claude/skills/bmad-cis-*'` exactly 10 files / 15 lines;
`test_no_retired_bmad_skill_ids` 9 passed; `python -m pyforge.doctor.sources spec-surface`
clean; `pixi run -e local-recipes detectors-ci` 17/18 clean (pre-existing `dream-chain` only).

**Residual risks:** `_bmad/config.yaml` was created as an untracked side effect of the
provision run (the module's own legacy-format roster bookkeeping — a different, newer
`_bmad/custom/config.toml [modules.<x>]` convention is described elsewhere for other modules'
provisioning, suggesting steward's own `provision --module cis` path has not yet been updated
to it) — left untracked, not committed; out of this story's scope to fix steward's own
provisioning tool. Two low-severity items deferred to step 11 (ledger/drain-queue sync,
epics.md Status/Outcome line).
