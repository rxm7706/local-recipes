---
title: 'Story 6.2 — The divergence-and-endgame guard, proven red first'
type: 'feature'
created: '2026-08-21'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
difficulty: ''
baseline_revision: '573d2861ea837276b9d1f1d56898ab58af23dfa6'
final_revision: '1510a022e6cc71a77fc67187d208b17b85bced53'
---

<intent-contract>

## Intent

**Problem:** The CFE-rebuild campaign (Epic 6) has no automated guard against its two known
failure modes — silent divergence between the live skill and a parallel replacement, and an
endgame that never arrives (the fate of the ~29,000-line `pyforge-atlas` rebuild, stranded
behind legacy code for months). Nothing currently reds CI when a slice's equivalence result
goes red/stale, when a CFE Rule-2 retro lands without being mirrored into an already-briefed
slice, or when a declared endgame still finds a caller resolving to legacy.

**Approach:** Add one repo-scope detector, `scripts/cfe_rebuild_guard_check.py` (registered in
`scripts/detectors.py` exactly like the existing `scripts/mason_cfe_surface_check.py`
precedent), that reads `campaign-state.yaml` (extended with three new state hooks below) plus
bounded git history to enforce all three clauses. Each clause is proven red by a fixture before
any slice lands, per the story's AC — this story ships the guard, not the rebuild.

## Boundaries & Constraints

**Always:**
- Single script, single pixi task (`cfe-rebuild-guard-check`), `DETECTOR = {"scope": "repo"}` —
  every input (campaign-state.yaml, git log) is tracked/committed state; nothing runtime-only.
- Clause (a): any slice whose `status` is `parallel`, `audited`, or `cut-over` must have
  `equivalence: "green"`; `equivalence` missing/null, `"red"`, or `"stale"` is a finding
  (`stale-equivalence`). The detector never computes staleness itself from timestamps — it
  trusts the recorded enum value (writing/refreshing it is the equivalence harness's job, out
  of this story's scope).
- Clause (b): a "landed CFE Rule-2 retro" = a commit in `806cb630469688d596cac00a53573f01f39386e2..HEAD`
  (this constant = the Story-6.1 landing merge, PR #570; overridable via `--since <sha>` so tests
  can bound a scratch repo) whose diff touches the CFE surface
  (`.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  `.claude/tools/conda_forge_server.py`) **and** touches
  `.claude/skills/conda-forge-expert/CHANGELOG.md` (status A or M) in the same commit. No
  commit-subject pattern is ever part of the test (this corrects the prior reverted attempt,
  which wrongly gated on a literal `retro:` subject prefix that no real CFE retro commit in this
  repo's history actually uses). For every slice with a non-null `brief_path`, if the newest
  qualifying retro SHA in range differs from that slice's `brief_mirrored_through`, that is a
  finding (`unmirrored-retro`). Slices with `brief_path: null` are never checked — no brief
  exists yet for anything to go stale.
- Clause (c): only evaluated when `campaign.endgame_declared: true`; any entry in
  `campaign.callers` with `resolves_to: "legacy"` is a finding (`legacy-caller-at-endgame`).
  While `endgame_declared` is false (true throughout Epic 6), this clause is vacuously clean —
  the real caller-resolution population is future cutover work, not this story's.
- Extend `campaign-state.yaml`'s real, tracked instance
  (`_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`)
  with the new fields at their inert defaults (`equivalence: null`, `brief_path: null`,
  `brief_mirrored_through: null` per slice; `endgame_declared: false`, `callers: []` at the
  `campaign:` level) and update its schema-documenting header comments — the real file must
  stay clean under the new detector the moment this story lands.
- Exit codes match `mason_cfe_surface_check.py`: 0 clean, 1 findings, 2 could not run (bad/missing
  campaign-state.yaml, or `git log` failed). `--json` machine output supported.
- Tests live at `tests/scripts/test_cfe_rebuild_guard_check.py`, real tmp git repos (the
  `_isolate_git_env` pattern from `test_mason_cfe_surface_check.py`), fabricated
  campaign-state.yaml fixtures — one red-proving case per clause, plus a clean-repo case.

**Block If:** N/A — no undetermined decision requires human input; all three clauses' detection
mechanics are fully specified above.

**Never:**
- Never gate clause (b) on any commit-subject-line pattern (this is the exact defect being
  corrected).
- Never confuse this detector's clause-(b) scope with `mason_cfe_surface_check.py`'s own,
  narrower `retro:`-subject sanctioned-exception check — that check is self-scoped to Mason's own
  commit history (FR-45/Story 5.5) and stays untouched.
- Never implement real caller-introspection for clause (c) or a real equivalence-harness runner
  for clause (a) — both are declared-state readers only; producing accurate values for those
  fields is later work (6.3 for equivalence; the eventual end-cutover effort for callers).
- Never touch any slice's `status` value or any other pre-existing campaign-state.yaml field.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean campaign | all slices `mapped`/`briefed` w/ matching `brief_mirrored_through`, `endgame_declared: false` | exit 0, no findings | — |
| Stale equivalence | a `parallel` slice, `equivalence: "stale"` | exit 1, `stale-equivalence` finding naming the slice | — |
| Unmirrored retro | slice w/ `brief_path` set, a fixture retro commit (CFE surface + CHANGELOG touch) lands after `brief_mirrored_through` | exit 1, `unmirrored-retro` finding naming slice + commit SHA | — |
| Retro commit without CHANGELOG touch | commit touches CFE surface only | not counted as a retro; no finding from it | — |
| Endgame with a legacy caller | `endgame_declared: true`, one caller `resolves_to: "legacy"` | exit 1, `legacy-caller-at-endgame` finding | — |
| campaign-state.yaml missing/unparseable | file absent or malformed YAML | exit 2, `UNKNOWN: ...` message (JSON: `{"error": ...}`) | never treated as clean |
| `git log` fails (not a repo) | subprocess error | exit 2, same UNKNOWN convention | never treated as clean |

</intent-contract>

## Code Map

- `scripts/cfe_rebuild_guard_check.py` -- new detector script, three clauses, modeled on `scripts/mason_cfe_surface_check.py`.
- `scripts/detectors.py` -- no edit needed; auto-discovers via the `*_check.py` glob + `DETECTOR` dict, same as every sibling.
- `pixi.toml` -- add `[feature.local-recipes.tasks.cfe-rebuild-guard-check]` beside the existing `mason-cfe-surface-check` block (~pixi.toml:653-655).
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml` -- add the three new state hooks at inert defaults + header comment update.
- `tests/scripts/test_cfe_rebuild_guard_check.py` -- new, fixture-based, modeled on `tests/scripts/test_mason_cfe_surface_check.py`.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/cfe_rebuild_guard_check.py` -- implement three-clause detector (constants, `campaign_state()` YAML loader, `retro_commits_since()` git scan, `scan()` producing findings, `main()` with `--json`/`--since`) -- the guard itself
- [x] `pixi.toml` -- register `cfe-rebuild-guard-check` task -- makes the detector discoverable/runnable per `scripts/detectors.py`'s pixi-task requirement
- [x] `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml` -- add `equivalence`/`brief_path`/`brief_mirrored_through` per slice and `endgame_declared`/`callers` under `campaign:`, all at inert defaults; update header comments describing the new fields -- keeps the real file green under the new detector
- [x] `tests/scripts/test_cfe_rebuild_guard_check.py` -- one red-proving fixture per clause (a/b/c) + one clean-repo case + the two `exit 2` unknown cases -- proves each clause red before any slice lands, per the story's AC

**Acceptance Criteria:**
- Given the real, unmodified `campaign-state.yaml` after this story's schema additions, when `pixi run -e local-recipes cfe-rebuild-guard-check` runs, then it exits 0 (clean).
- Given a fixture repo with a slice `status: parallel` and `equivalence: "red"`, when the detector runs against it, then it exits 1 with a `stale-equivalence` finding.
- Given a fixture repo with a `brief_path`-set slice and a synthetic commit (after the fixture's `--since` boundary) touching both the CFE surface and CHANGELOG.md, with no corresponding `brief_mirrored_through` update, when the detector runs, then it exits 1 with an `unmirrored-retro` finding — regardless of that commit's subject line (tested with a subject that does NOT start `retro:`, to prove clause (b) is subject-pattern-independent).
- Given `endgame_declared: true` and one `callers` entry `resolves_to: "legacy"`, when the detector runs, then it exits 1 with a `legacy-caller-at-endgame` finding.
- Given `python3 scripts/detectors.py --list`, when run after this story lands, then `cfe_rebuild_guard_check` appears in the `repo` detector list with its pixi task.

## Spec Change Log

None — no bad_spec loopback occurred; the corrected intent-contract held on this run.

## Review Triage Log

### 2026-08-21 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 0, medium 1, low 4)
- defer: 3 (high 0, medium 0, low 3)
- reject: 6 (high 0, medium 0, low 6)
- addressed_findings:
  - `[medium]` `[patch]` `scan()` crashed with `AttributeError` on a non-dict `slices`/`campaign`/slice-entry shape instead of the documented exit-2 UNKNOWN contract — added `isinstance` guards at all three sites (`slices` container, per-slice entries, `campaign`); confirmed the crash reproduces pre-fix and is gone post-fix; two new tests added (`test_scan_tolerates_non_dict_slice_entries`, `test_scan_tolerates_non_dict_campaign`).
  - `[low]` `[patch]` `diff_name_status()`'s 3-field rename/copy diff-line parsing (`status\told\tnew`) mis-split into a garbled path — extracted `_parse_name_status_lines()` and fixed to always take the last tab-separated field as the current path; confirmed via a real `git diff-tree -M` fixture that the fix resolves an actual rename line correctly (`test_diff_name_status_resolves_rename_line_to_new_path`). Note: verified this path is not reachable through the module's own (no `-M`/`-C`) git invocations today — defensive hardening, not a live-bug fix; test docstring says so explicitly.
  - `[low]` `[patch]` empty-string `brief_path` was treated as "has a real brief" (only `is None` was skipped) rather than as equivalent to `null` — changed to a falsy check (`if not brief_path: continue`); new test `test_unmirrored_retro_empty_string_brief_path_treated_as_null`.
  - `[low]` `[patch]` clause (b)'s "newest qualifying retro" comparison used default (non-topological) commit order — added `--topo-order` to the `git log` invocation in `retro_commits_since()`; commit *set* is unaffected, only ordering, so no test change needed beyond the existing suite staying green.
  - `[low]` `[patch]` JSON error payload (`_unknown()`) omitted the `retros_scanned` key present on the success-path payload, unlike the sibling `mason_cfe_surface_check.py`'s `commits_scanned: None` parity — added `"retros_scanned": None` to the error payload; `test_main_exit_2_json_still_emits_json` extended to assert it.
  - `[low]` `[defer]` `DW-6-2-1` — clause (b)'s commit scan has no advancing anchor, so per-run git cost grows monotonically for the campaign's life; acceptable now (deliberate simplicity tradeoff, self-bounded by the Story-6.4 re-scope gate), revisit if the campaign extends past the pilot slice.
  - `[low]` `[defer]` `DW-6-2-2` — `mason_cfe_surface_check.py` (FR-45/Story 5.5, out of this story's scope) has the identical un-patched rename-parsing pattern this story fixed in its own new script; flagged for whoever next touches that file.
  - `[low]` `[defer]` `DW-6-2-3` — the hardcoded `DEFAULT_SINCE` anchor has no fallback if that commit is ever rewritten out of history; tied to the already-separately-deferred 2026-07-24 force-push rewrite, not actionable now.
  - `[low]` `[reject]` "`endgame_declared` should use a lenient truthy check" — rejected: the current strict `is True` check is the *safer* choice (a lenient `bool(...)` check would make the YAML string `"false"` also evaluate truthy in Python, a worse regression).
  - `[low]` `[reject]` "the two live-repo assertions are currently vacuous" (every slice is `mapped`, no clause can fire yet) — rejected: by design, per the story's own Design Notes; the fixture tests (not the live-repo ones) are what proves each clause red per the AC.
  - `[low]` `[reject]` "campaign-state.yaml's new header comment duplicates the script docstring, no sync enforcement" — rejected: deliberate, matching CAP-4's "resumable from state alone" intent — a fresh session must understand the schema from campaign-state.yaml alone, without opening the detector script.
  - `[low]` `[reject]` "`environment.yaml` regeneration step missing from the diff" — rejected as a code-diff finding: verified `pixi project export conda-environment -e build` is currently byte-identical to the tracked file (task-only `pixi.toml` change, no new dependency); regeneration is re-checked at landing per this repo's standing PR-open procedure regardless.
  - `[low]` `[reject]` "`maintenance` label requirement not demonstrable from the diff" — rejected as a code-diff finding: PR metadata, not a file change; applied at PR-open time per this repo's standing procedure, outside this review's visibility.
  - `[low]` `[reject]` "the story's spec was not yet promoted to tracked `planning-artifacts/specs/`" — rejected as a code-diff finding: per CLAUDE.md's own convention, promotion happens *after* the story merges, not before — correctly out of scope for a pre-merge review pass.

## Design Notes

Clause (b)'s "affected slice" test is deliberately coarse: any retro commit landing after a
slice's `brief_mirrored_through` checkpoint counts against that slice, with no attempt to
content-diff the retro's touched files against slice-map.md's per-slice file coverage. This is
intentional, not a shortcut left for later — it trades precision for the anti-atlas property
this whole detector exists to guarantee (never silently under-flag); a false positive here costs
a maintainer one look at a retro's CHANGELOG entry, a false negative costs silently stale
knowledge in a parallel-run replacement. Refining it to real per-slice file targeting, if ever
wanted, is separable follow-up work, not a gap in this story.

SPEC.md's CAP-3 text still points to `scripts/dream_chain_check.py` as the structural style
precedent; that script no longer exists as a scanned file (Story 6.9 ported it into
`pyforge.doctor.sources`, an in-process gather with no file for `detectors.py` to AST-scan). The
live, current precedent is `scripts/mason_cfe_surface_check.py`, which this story follows
instead — noted here so a future reader doesn't chase the dead reference.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary of implemented change:** Added `scripts/cfe_rebuild_guard_check.py`, a new
repo-scope detector for pyforge-mason Epic 6's CAP-3 (registered in `scripts/detectors.py`
via its `DETECTOR = {"scope": "repo"}` dict, discovered the same way as the precedent
`mason_cfe_surface_check.py`). It enforces three clauses over `campaign-state.yaml` +
bounded git history: (a) `stale-equivalence` — a `parallel`/`audited`/`cut-over` slice must
have `equivalence: "green"`; (b) `unmirrored-retro` — a landed CFE Rule-2 retro (detected by
CFE-surface-touch + CHANGELOG.md touch in the same commit, bounded to `806cb63046..HEAD`,
Story 6.1's landing merge — **never** by commit-subject pattern, correcting the prior
reverted attempt's defect) must be mirrored into any briefed slice's `brief_mirrored_through`;
(c) `legacy-caller-at-endgame` — once `campaign.endgame_declared` is true, no caller may
still resolve to legacy. `campaign-state.yaml` was extended additively with the three new
state hooks these clauses read.

**Files changed:**
- `scripts/cfe_rebuild_guard_check.py` (new) — the three-clause detector.
- `tests/scripts/test_cfe_rebuild_guard_check.py` (new) — 29 tests, real tmp-git-repo fixtures, one red-proving case per clause plus the review-driven robustness cases.
- `pixi.toml` (modified) — registered the `cfe-rebuild-guard-check` task.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml` (modified) — additive schema: `equivalence`/`brief_path`/`brief_mirrored_through` per slice, `endgame_declared`/`callers` under `campaign:`.

**Review findings breakdown:** 5 patches applied (1 medium: a crash-instead-of-exit-2 gap on malformed nested YAML shapes; 4 low: rename-line parsing hardening, empty-string `brief_path` handling, `--topo-order` for deterministic "newest retro" selection, JSON error-payload key parity with the sibling detector), 3 deferred (`DW-6-2-1/2/3`, all low, logged to the Tier-3 deferred-work feed — none block this story), 6 rejected (by-design or out-of-code-diff-scope: the endgame-flag strictness, the vacuous-while-nothing-has-progressed live-repo tests, deliberate schema/docstring duplication, and three landing-procedure items — `environment.yaml` regen, the `maintenance` PR label, and post-merge spec promotion — that are handled by this repo's standing landing procedure rather than this code diff). Zero intent_gap, zero bad_spec — the corrected intent-contract held; no loopback needed.

**Verification performed:** `pixi run -e local-recipes pytest tests/scripts/test_cfe_rebuild_guard_check.py -v` — 29/29 pass. `pixi run -e local-recipes cfe-rebuild-guard-check` — exit 0, clean, against the real unmodified campaign-state.yaml. `python3 scripts/detectors.py --list` — `cfe_rebuild_guard_check` present under `repo` with its pixi task. `pixi run --frozen -e pyforge-mason pyforge-mason-test` — 1534 passed, 3 deselected, unaffected. `pixi run -e local-recipes pytest tests/scripts/test_mason_cfe_surface_check.py -q` — 48/48 pass, sibling detector unaffected. Independently re-verified clause (b)'s retro-detection logic by hand against real git history (`git log 806cb63046..HEAD`, `git log -- CHANGELOG.md`): 0 qualifying retro commits in range, correctly excluding the pre-boundary retro commits (v8.75.0 through v8.82.x) that would have false-positived under the prior reverted attempt's unbounded design.

**Residual risks:** All three `defer` items are low-severity and non-blocking (see above; logged as `DW-6-2-1/2/3`). No high or unaddressed medium findings remain. `followup_review_recommended: false` — the patched findings are small, well-contained, and individually well-tested; none touch behavior/API/security/data-integrity surface beyond what the fixture suite already exercises.
