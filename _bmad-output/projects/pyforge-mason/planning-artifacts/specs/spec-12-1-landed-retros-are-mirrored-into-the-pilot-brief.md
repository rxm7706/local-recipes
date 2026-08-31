---
title: Landed retros are mirrored into the pilot brief
type: chore
created: '2026-08-27'
status: done
updated: '2026-08-27'
# Implementation 2026-08-27 (session died on usage limit; work preserved as WIP commit
# fed0094fd3 by redispatch); review pass completed same day by bmad-build-auto (see
# Review Triage Log + Auto Run Result). Landing + ledger flip remain the dispatcher's.
# baseline_revision was re-pointed cc8b3b2b -> 5bae7d33 at redispatch: the dispatch
# worktree branches from the PR #882 merge (main at dispatch time), so the reviewed
# diff covers exactly this story's changes.
baseline_revision: 5bae7d330164a14de41ca789d8edefeab858a213
review_loop_iteration: 0
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-2-the-divergence-and-endgame-guard-proven-red-first.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-3-pilot-slice-recipe-generation-built-and-parallel-validated.md
warnings: []
deferred:
  - summary: >-
      Guard clause (b) never opens the brief it certifies -- brief_mirrored_through is a
      pure string equality against tracked YAML, so a re-lost or hollowed-out
      skill-brief.yaml ships green.
    evidence: |-
      scripts/cfe_rebuild_guard_check.py:223-245 uses brief_path for truthiness only and
      never reads or stats the file; all 29 tests construct synthetic state dicts; a
      repo-wide symbol search found no other automated consumer of the brief, and the
      dual-copy durability arrangement (worktree + main tree) has no ongoing sync check.
      Natural owner: Story 12.4's clause-(d) detector addition (a runtime-scope check
      that the brief exists and its amendments name the mirrored SHAs).
    location: >-
      scripts/cfe_rebuild_guard_check.py:227
    severity: medium
  - summary: >-
      Slice-1 "equivalence: green" is stale relative to CFE v8.84.0, and guard clause (a)
      will pass a future compiled->parallel advancement -- the "re-port/re-validate before
      advancing" gate exists only as prose in next_action.
    evidence: |-
      Clause (a) gates only parallel/audited/cut-over and trusts the recorded enum
      (cfe_rebuild_guard_check.py:198-218; the existing tests pin both behaviors).
      Recording the staleness machine-readably (an equivalence value or an
      equivalence_as_of SHA that clause (a) can compare) belongs to the slice-1
      re-validation work (Story 12.3's real-audit pass) -- this chore's intent authorized
      only the brief mirror + pointer flip, and rewriting the recorded green would
      falsify the corpus it was legitimately run against.
    location: >-
      _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml:313
    severity: medium
  - summary: >-
      The new "retro-mirror" amendment action is outside skf consumer enums, and
      skill-brief.v1.json does not constrain scope.amendments at all -- "schema valid"
      never inspected the new entries.
    evidence: |-
      skf-provenance-gap-dispatch.py::_classify has a fixed action set
      (promoted/skipped/demoted-*); retro-mirror falls through to unresolved, which is
      fail-safe (surfaces for attention rather than hiding). The consequence path is
      speculative today -- both retro-mirrored paths are already in scope.include -- but
      recorded so the next skf schema/enum touch adds retro-mirror deliberately.
    severity: low
---

<intent-contract>

## Intent

**Problem:** `pixi run -e local-recipes cfe-rebuild-guard-check` reports a live
`unmirrored-retro` finding today: 4 commits in `806cb63046..HEAD` qualify as landed CFE
Rule-2 retros (CFE-surface touch + `CHANGELOG.md` A/M in the same commit — mechanical, never
subject-pattern-based), newest `565ef7d194`, and slice 1's `brief_mirrored_through` is still
`null`. Nothing has re-opened this duty since Story 6.2 shipped the detector.

**Approach:** Read each of the 4 qualifying commits' real diff (not just its subject or
CHANGELOG one-liner), mirror the actual CFE-surface delta into slice 1's brief, then set
`brief_mirrored_through` to the newest qualifying SHA and confirm the detector goes clean.
The detector, not this story, re-opens the duty the next time a retro lands unmirrored.

## Acceptance Criteria

- **Given** the guard's live clause-(b) finding (4 qualifying CFE Rule-2 retros in
  `806cb63046..HEAD`, newest `565ef7d194`, none mirrored; `brief_mirrored_through: null`)
  **Then** each landed retro's CFE-surface delta is mirrored into slice 1's brief,
  `brief_mirrored_through` records the newest mirrored SHA, and
  `pixi run -e local-recipes cfe-rebuild-guard-check` exits clean — the detector, not this
  story, re-opens the duty on the next unmirrored retro.

## Boundaries & Constraints

**Always:**
- Write artifacts under `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-mason` only — never `scripts/bmad-switch`. Ledger key
  `12-1-landed-retros-are-mirrored-into-the-pilot-brief`.
- Mirror all 4 qualifying commits' actual CFE-surface delta (read each via `git show <sha>`,
  not just its one-line subject) into slice 1's brief content, then set
  `campaign-state.yaml`'s `slices[0].brief_mirrored_through` to the newest SHA
  (`565ef7d194b1ccd740951250aa6535b65bdfc7b6`).
- Re-run `pixi run -e local-recipes cfe-rebuild-guard-check` and confirm exit 0 before closing.

**Block If:** The brief target
(`_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data/cfe-recipe-generation/skill-brief.yaml`,
per `campaign-state.yaml`'s `brief_path`) cannot be located or reconstructed in this
worktree — HALT and report rather than fabricating brief content Story 6.3 never actually
authored here.

**Never:**
- Never edit `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  or `.claude/tools/conda_forge_server.py` (CFE surface) — mason consults CFE, never edits it
  (mason-cfe-surface-check gate). Reading each commit's diff against that tree is fine;
  editing anything under it is not.
- Never gate which commits count as "real" retros on their subject line — the detector's
  clause (b) is mechanical (CFE-surface touch + CHANGELOG.md touch), and this story's
  judgment about what to actually mirror must come from each commit's real diff.
- Never touch `epics.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean run | Brief mirrored, `brief_mirrored_through` set to `565ef7d194b1ccd740951250aa6535b65bdfc7b6` | `cfe-rebuild-guard-check` exits 0 | — |
| Brief target missing | Tier-3 `forge-data/cfe-recipe-generation/` absent in this worktree | Halt, name the physical path checked | Never fabricate a brief from scratch |
| A 5th retro lands mid-story | New qualifying commit lands after work starts | Re-check `--json` output's newest SHA before closing; mirror it too | A stale `brief_mirrored_through` re-opens on the next detector run |
| Commit is a merge / feature commit, not an obvious "retro" (e.g. `621ab29c`, `2d276ecb`) | Mechanically qualifies per clause (b) | Still mirror its actual CFE-surface delta honestly, even if the note is short | Never silently skip a mechanically-qualifying commit |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — slice `slice-1-recipe-generation`'s `brief_mirrored_through: null` (line 293) → set to
  `565ef7d194b1ccd740951250aa6535b65bdfc7b6` once mirrored.
- Slice 1's brief target,
  `_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data/cfe-recipe-generation/skill-brief.yaml`
  (campaign-state.yaml line 292) — CONFIRMED ABSENT in this worktree: `forge-data/` here
  contains only `cf-atlas-legacy/` and `.gitkeep`, no `cfe-recipe-generation/` subdirectory.
  This is gitignored Tier-3, per-worktree state (the same class of gap as GATHERED GAPS #1's
  `forge-tier.yaml`) — locating or reconstructing it is this story's first real task, not an
  assumed-solved precondition.
- The 4 qualifying commits to mirror, newest first: `565ef7d194b1ccd740951250aa6535b65bdfc7b6`
  (merge PR #676, 2026-08-23, steward 15-2 one-command suite advance),
  `621ab29c72a22b2b900144be20b74823dffe36cc` (2026-08-23, the underlying steward 15-2 feat
  commit), `2d276ecbf4bce613c369507ae74dc283de016b2c` (merge PR #606, 2026-08-21, bmad-method
  v6.11.0 update), `6ace3fd6ab204324dffc2ec4c5e1133749d4e6c5` (2026-08-21, "cfe: v8.83.0 —
  Rule-2 retro for the bmad-suite refresh"). `git show <sha>` each one for its real
  CFE-surface delta rather than restating the subject line.
- `scripts/cfe_rebuild_guard_check.py` — read-only; defines clause (b)'s exact detection
  mechanics (`retro_commits_since()`, `DEFAULT_SINCE = "806cb630469688d596cac00a53573f01f39386e2"`)
  — ground truth for what "qualifying" means. Do not edit its logic (that is Story 12.4's
  clause-(d) addition, not this story's).
- `.claude/skills/cfe-recipe-generation/1.0.0/cfe-recipe-generation/metadata.json` — the
  compiled package's own record of which source scripts it ported and why (a distinct,
  non-CFE-surface skill tree); a useful cross-check for what the brief should already
  reflect.

## Tasks & Acceptance

**Execution (2026-08-27):**
- [x] Locate/reconstruct the brief target — CONFIRMED ABSENT in this worktree AND the main
  tree (`forge-data/` holds only `cf-atlas-legacy/` + `.gitkeep`); the authoring worktree
  (`.claude/worktrees/agent-a00a0f6206d94a499`, per the compiled package's
  `metadata.json:source_repo`) is torn down. RECONSTRUCTED verbatim from the authoring
  session's transcripts (full path, resolved at review:
  `~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/bb1777ca-2cee-49f5-861c-a25229c850c0/subagents/agent-a13bf77a53f12f805.jsonl`):
  the initial `skf-write-skill-brief.py` draft was recovered from a Read tool-result, and the
  two 2026-08-21 amendment scripts (`add_skip_amendments.py` — 24 headless auth-doc skip
  amendments from the surviving candidates JSON `tool-results/bljugy7rw.txt`;
  `add_runtime_dep_amendment.py` — `_cfy_template.py` + 7 templates scope expansion) were
  replayed exactly. Byte-verified against both recorded `skf-atomic-write` receipts:
  8370 bytes after amendment 1, 11634 bytes final — exact match on both checkpoints.
- [x] Read all 4 qualifying commits' real diffs (`git show`/`diff-tree`/`--numstat`, never
  the subject line): they are two substantive CFE deltas, each landing twice (feat + merge) —
  CFE v8.83.0 = `6ace3fd6`/`2d276ecb` (PR #606: SKILL.md +G109/+G110, cheatsheet
  SelfExplainML publish flow, version files); CFE v8.84.0 = `621ab29c`/`565ef7d194` (PR #676:
  `github_updater.py` +167/−9 — `update_recipe_head()` + `_fetch_default_branch_head()` +
  `--head` CLI, HEAD-advance for commit-pinned recipes; version files).
- [x] Mirror both deltas into the brief as two dated `scope.amendments` entries
  (`action: retro-mirror`, `category: dual-landing`, each listing both its feat and merge
  SHAs) plus a dated `scope.notes` section recording the reconstruction provenance, the
  dual-landing mirror, and the historical correction that the brief's pre-existing
  "THIRD, NOT fixed" `github_version_checker.py` claim was superseded by Story 6.3's
  gap-closure pass (operator-decided port, `ec193303b6`). Brief re-validated with the real
  `skf-validate-brief-schema.py`: `valid: True`, 0 errors, 0 warnings. Implementation-time
  brief = 16400 bytes, sha256
  `01f4284c26e1b3cc3c7711a4b4b215eeb07b6fc98e11d813d233706cd792f24f` (full hash recorded at
  review; the review pass later appended a READING NOTE — post-review final in Auto Run
  Result); a byte-identical durability copy was also placed at
  the same gitignored path in the main tree (this worktree is disposable — leaving the only
  copy here would re-create the exact Tier-3 loss this story just repaired).
- [x] `campaign-state.yaml` — `slices[0].brief_mirrored_through: null →
  "565ef7d194b1ccd740951250aa6535b65bdfc7b6"` (full 40-char SHA — the detector compares
  `%H` output by equality); replaced the field's now-false "0 retros in range" comment;
  appended the v8.84.0 divergence consequence to slice-1's `next_action` (compiled
  `github_updater.py` copy is now BEHIND live; re-port/re-validate before slice 1 advances
  past `compiled`; the recorded `equivalence: green` predates v8.84.0); `last_updated →
  2026-08-27`. Nothing else touched — no `status`/`equivalence` value changed, `epics.md`
  and `sprint-status-ledger.yaml` untouched, CFE surface untouched (read-only `git show`).

**Acceptance Criteria (verified):**
- `pixi run -e local-recipes cfe-rebuild-guard-check` — exit 0, "clean", after reporting
  "4 qualifying CFE retro commit(s) in 806cb63046..HEAD". `--json`: `{"retros_scanned": 4,
  "findings": []}`.
- 5th-retro edge case re-checked at close: HEAD is `5bae7d3301` (= this spec's
  `baseline_revision`), newest qualifying retro unchanged at `565ef7d194…`.
- `pixi run -e local-recipes pytest tests/scripts/test_cfe_rebuild_guard_check.py -q` —
  29/29 pass (detector logic untouched, as required).

## Review Triage Log

### 2026-08-27 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 0, medium 1, low 7)
- defer: 3: (high 0, medium 2, low 1)
- reject: 5: (high 0, medium 0, low 5)
- addressed_findings:
  - `[medium]` `[patch]` Auto Run Result claimed the change set was "uncommitted" and the
    5th-retro re-check implied HEAD = baseline — both stale once the redispatch preserved
    the work as WIP commit `fed0094fd3`; Auto Run Result rewritten with the true
    commit/tree state, and every AC command independently re-run at the current HEAD.
  - `[low]` `[patch]` `baseline_revision` had been silently re-pointed
    `cc8b3b2b → 5bae7d33`; the frontmatter comment now records the redispatch re-baseline
    rationale.
  - `[low]` `[patch]` The reconstructed brief's sha256 was recorded only truncated;
    full implementation-time hash now in Tasks, post-review final hash below.
  - `[low]` `[patch]` The transcript provenance path was elided (`…/bb1777ca-…/…`);
    the full physical path is now recorded in Tasks.
  - `[low]` `[patch]` The reconstructed brief still carried the stale "do not widen
    scope.include beyond the 8 paths above" instruction and the pre-gap-closure 59/60
    figure with no correction; a READING NOTE was appended inside the story-12.1 section
    of `scope.notes` (append-only convention preserved — historical bytes untouched),
    schema re-validated, both tree copies re-synced.
  - `[low]` `[patch]` "No content hash of the original survives" was asserted unchecked;
    the compiled package's `metadata.json` is now positively verified to carry no brief
    hash (its sha256 entries are ported-source hashes) — the claim stands, now evidenced.
  - `[low]` `[patch]` Frontmatter integrity after comment insertion had not been
    re-verified; the full frontmatter now parses as YAML post-edit (recorded below).
  - `[low]` `[patch]` Why the brief stays untracked was undocumented; the Tier-3 boundary
    (gitignored `implementation-artifacts/`, the `tracked-impl-artifact` HARD rule) is now
    named below as the reason promotion/tracking was not an option.

## Auto Run Result

Status: done. Review pass completed 2026-08-27 by bmad-build-auto (redispatch — the
implementing session died on a usage limit; its work survived intact as WIP commit
`fed0094fd3` and nothing was re-implemented).

**Implemented change:** reconstructed the lost Tier-3 slice-1 skill brief verbatim from the
authoring session's transcripts, mirrored the 4 qualifying CFE Rule-2 retros (two
substantive deltas, each landed as feat + merge) into it as two dated `retro-mirror`
amendments plus provenance/correction notes, set `campaign-state.yaml`'s
`slices[0].brief_mirrored_through` to `565ef7d194b1ccd740951250aa6535b65bdfc7b6`, and
confirmed the detector clean.

**Files changed:**
- `…/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml` — pointer `null →` newest
  retro SHA; now-false "0 retros" comment replaced; v8.84.0 divergence consequence appended
  to slice-1 `next_action`; `last_updated` bumped.
- `_bmad-output/projects/pyforge-atlas/implementation-artifacts/forge-data/cfe-recipe-generation/skill-brief.yaml`
  (gitignored Tier-3; worktree + byte-identical main-tree durability copy) — reconstructed
  2026-08-21 original + story-12.1 additions + review-pass READING NOTE. Post-review final:
  16886 bytes, sha256
  `4e4673aaaca7bbcad8c196060e7d5fb18b1ac57f6e64ec1233ecc9c4f5d0f69c`, `valid: True`,
  0 errors, 0 warnings. Stays untracked by design: `implementation-artifacts/` is
  gitignored Tier-3 and the `tracked-impl-artifact` HARD rule forbids promotion.
- This spec file — execution record, review triage log, deferred findings.

**Review findings breakdown:** 4 parallel layers (blind, edge-case, verification-gap,
intent-alignment). intent_gap 0; bad_spec 0; **8 patches applied** (1 medium, 7 low — all
documentation-surface accuracy fixes, no code or campaign-semantics change); **3 deferred**
(2 medium, 1 low — in frontmatter `deferred`); 5 rejected. Intent alignment: the diff
implements the Block-If's sanctioned "or reconstructed" reading; all Never-clauses hold
(CFE surface, `epics.md`, `sprint-status-ledger.yaml` untouched; retro qualification never
subject-gated — the mirrored set includes a feature commit and two PR merges).

**Follow-up review recommendation: true** — patched counts high 0, medium 1, low 7; score
= 3×1 + 1×7 = 10 ≥ 5. (Composition note: every patch was spec/brief prose accuracy.)

**Verification performed (re-run at review close, 2026-08-27, HEAD past `fed0094fd3`):**
- `pixi run -e local-recipes cfe-rebuild-guard-check` — exit 0, "clean", 4 retros scanned;
  re-run after the review-pass brief append.
- `pixi run -e local-recipes pytest tests/scripts/test_cfe_rebuild_guard_check.py -q` —
  29/29 pass (detector logic untouched, as required).
- Brief present in worktree AND main tree, byte-identical, sha256 checked before and after
  the review-pass append; schema validator re-run after the append.
- Spec frontmatter parsed as YAML post-edit; `deferred` is a single list with all 3 items.
- No CFE-surface commit landed on `main` after the baseline (`git log 5bae7d33..main` over
  the CFE surface is empty) — no 5th qualifying retro; newest remains `565ef7d194…`.

**Residual risks:** (1) the brief is durable only as two gitignored copies with no
automated existence/sync check — deferred finding 1 (natural owner: Story 12.4's
clause-(d) detector work); (2) the reconstruction is receipt-byte-verified, not
hash-verified against the lost original — `metadata.json` positively confirmed to carry no
brief hash; (3) the compiled `github_updater.py` remains BEHIND live with a stale
`equivalence: green` — deferred finding 2 (owner: Story 12.3's re-validation).

Landing, the ledger flip for key `12-1-landed-retros-are-mirrored-into-the-pilot-brief`,
and the `maintenance` PR label remain the dispatcher's; no `recipes/**` or `pixi.toml`
change, so no env-sync.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
