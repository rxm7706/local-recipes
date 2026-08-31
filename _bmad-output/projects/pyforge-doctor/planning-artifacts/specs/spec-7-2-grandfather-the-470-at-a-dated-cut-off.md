---
title: 'Story 7.2: Grandfather the 470 at a dated cut-off'
type: 'feature'
created: '2026-08-11'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '500bfe55282399eb7c3ae862de57e8949841218d'
final_revision: '183f345b9baf9cffe1c54b26fc73a64b7f29b04f'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-7-context.md'
  - '{project-root}/.claude/skills/bmad-loop-sweep/deferred-work-format.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Story 7.1 fixed the emitter, but a real backlog sits behind it: 506 pre-existing
anonymous `- source_spec:` bullets across the fleet's 8 projects' gitignored `deferred-work.md`
files (measured live via `chain.py`'s own `_anonymous()` algorithm: marshal 207, doctor 72,
steward 71, atlas 54, warden 41, herald 33, mason 22, scribe 6 -- the epic's own "470" is
already stale, which is exactly why a fixed count cannot be the mechanism). Once Story 7.3 arms
`_anonymous()` against the Tier-3 file, every one of these becomes a FAIL on an otherwise-
unchanged repo unless something exempts them first.

**Approach:** Mirror Doctor's own shipped precedent for exactly this shape (`gather_spec_surface`'s
read-only judge + `scripts/spec_surface_check.py --write-baseline`'s committed JSON baseline,
Story 6.9): a new mutation-only script, `scripts/deferred_work_baseline.py`, computes each
project's CURRENT count of anonymous Tier-3 entries and stamps them into a new committed
`scripts/.deferred-work-baseline.json` as `{project_slug: count}`. The git commit that
introduces this file IS the dated cut-off; Story 7.3 arms the actual comparison later.

## Boundaries & Constraints

**Always:**
- The baseline is a flat `{project_slug: int}` JSON mapping -- one count per project, the total
  number of anonymous Tier-3 entries (per chain.py's own `_anonymous()` algorithm) observed at
  stamping time. No per-entry ids, hashes, or line numbers -- Tier-3 entries have no stable
  identity to key by (that is the whole reason they're anonymous), and the file's own
  append-only discipline (verified live: no code path in this repo ever deletes, reorders, or
  inserts above an existing Tier-3 entry -- `land.py::_promote_deferred_work` only ever reads
  Tier-3 text and appends to the TRACKED ledger; `normalize_deferred_ledgers.py` rewrites only
  the tracked ledger; `deferred-work-format.md` states the Tier-3 file is "append-only -- never
  rewrite or delete existing entries") makes a positional count sufficient.
- `--write-baseline` (bare, no `--project`) recomputes and stamps EVERY discovered project (any
  `_bmad-output/projects/*/` with an `implementation-artifacts/deferred-work.md`).
  `--write-baseline --project SLUG` (repeatable) recomputes ONLY the named project(s) and
  MERGES into the existing committed file, leaving every other project's stamped count
  untouched -- mirrors `spec_surface_check.py`'s own scoped-stamping rationale: an all-or-
  nothing stamp would silently accept every OTHER project's growth as "always was this way."
- The script duplicates (never imports) chain.py's `_ENTRY_RE`/`_ANON_RE`/`_anonymous()` logic,
  exactly as `spec_surface_check.py` already duplicates its own algorithm rather than importing
  `pyforge.doctor` -- every `scripts/*.py` file must run standalone with plain `python`, no
  package install required.
- Unknown `--project` name(s) (not among currently-discovered projects) -> usage error, exit 2,
  listing the known set. `--project` without `--write-baseline` -> usage error, exit 2. Bare
  invocation (no flags at all) -> exit 2, explains what the script stamps and that a future
  story (7.3) is what will eventually consume it -- never claim the detector already reads this
  file, since it does not yet.
- Every discovered project gets a stamped entry, including a project whose current count is 0.
- Execute the script for real against this repo and commit the resulting
  `scripts/.deferred-work-baseline.json`, covering every currently-discovered project -- the
  epic's actual deliverable is the grandfathered backlog existing, not just the tooling.

**Block If:** None -- every resolution path above is fully defined; no ambiguity requires human
input.

**Never:**
- Never touch `pyforge.doctor.sources.chain` (`_anonymous`/`_ids`/`_ENTRY_RE`/
  `gather_deferred_work`) or wire the baseline into any read-side judgment -- that is Story
  7.3's job; this story produces the data file only (Doctor sources stay read-only: "the
  baseline file this epic introduces is data the detector reads, not a side effect it produces
  during a check run").
- Never baseline the TRACKED ledger (`deferred-work-ledger.md`) -- its own `_anonymous()` check
  is already live today and measured clean (0 anonymous entries across all 8 projects); there
  is no pre-existing backlog there to grandfather.
- Never add a pixi task for `--write-baseline` -- mirrors `spec_surface_check.py`'s own
  precedent (plain `python scripts/deferred_work_baseline.py --write-baseline`, no pixi
  wrapper; the existing `deferred-work-check` pixi task is the unrelated, unchanged read side).
- Never retrofit ids onto the anonymous entries themselves, and never triage whether any of the
  ~500 backlog entries are worth keeping -- both explicitly out of this epic's scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Bare `--write-baseline` | fresh repo, N projects each with a Tier-3 file | `.deferred-work-baseline.json` created/overwritten with all N projects' current anonymous counts | No error |
| `--write-baseline --project pyforge-doctor` | baseline already exists for 8 projects | only `pyforge-doctor`'s entry changes; other 7 byte-identical after | No error |
| `--project` names an unknown project | e.g. `--project pyforge-nope` | nothing written | exit 2, stderr lists known projects |
| `--project` given, `--write-baseline` omitted | any state | nothing written | exit 2, stderr says `--project` needs `--write-baseline` |
| No flags at all | any state | nothing written | exit 2, stderr explains the script's purpose |
| A project's Tier-3 file has 0 anonymous entries | all entries already carry `## DW-` headings | project stamped with count `0` | No error |
| A project directory exists but has no Tier-3 file at all | e.g. brand-new project | project not included in the stamp | No error |

</intent-contract>

## Code Map

- `scripts/deferred_work_baseline.py` -- NEW. Mutation-only baseline stamper; mirrors
  `scripts/spec_surface_check.py`'s shape (argparse, `--write-baseline`/`--project`,
  merge-not-rewrite, `json.dumps(..., indent=1, sort_keys=True)`).
- `scripts/.deferred-work-baseline.json` -- NEW, committed. The stamped `{project_slug: count}`
  data, produced by running the script above for real against this repo.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py:1323-1373` --
  READ-ONLY reference. `_ENTRY_RE`/`_ANON_RE`/`_anonymous()` is the exact algorithm the new
  script duplicates; not edited by this story.
- `scripts/spec_surface_check.py` -- READ-ONLY reference. The precedent this story's script
  structurally mirrors (argparse shape, scoped-merge semantics, JSON formatting, exit codes).
- `.claude/skills/bmad-loop-sweep/deferred-work-format.md` -- READ-ONLY reference. Documents
  the append-only discipline this story's positional-count design depends on.
- `tests/scripts/test_deferred_work_baseline.py` -- NEW. Coverage mirroring
  `.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py`'s own scoped-stamp
  test shape; picked up automatically by the existing `pyforge-doctor-scripts-test` pixi task
  (`pytest tests/scripts -q`), no pixi.toml change needed.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/deferred_work_baseline.py` -- create the mutation-only stamper (argparse
  `--write-baseline`/`--project`, duplicated `_anonymous()` algorithm, scoped merge,
  known-project validation) -- the tool that produces the grandfather baseline Story 7.3 will
  read.
- [x] `tests/scripts/test_deferred_work_baseline.py` -- cover every I/O matrix row against a
  real tmp-path fixture tree (per-project `deferred-work.md` fixtures, mirroring the spec-
  surface precedent's own fixture-repo helper) -- proves scoped stamping, merge-not-rewrite,
  and every error path actually fire.
- [x] `scripts/.deferred-work-baseline.json` -- run
  `python scripts/deferred_work_baseline.py --write-baseline` for real against this repo and
  commit the result -- the epic's actual deliverable: every currently-anonymous Tier-3 entry
  across all 8 projects is now covered by the baseline.

**Acceptance Criteria:**
- Given a repo with N discovered projects, when `--write-baseline` runs with no `--project`,
  then `scripts/.deferred-work-baseline.json` contains exactly N entries, each equal to that
  project's live anonymous-entry count.
- Given an existing baseline file, when `--write-baseline --project SLUG` runs, then only
  `SLUG`'s entry changes and every other project's previously-stamped count is byte-identical
  afterward.
- Given the real repo state, when the story lands, then `scripts/.deferred-work-baseline.json`
  is committed and its counts equal the measured anonymous-entry counts for every one of the 8
  currently-known projects (marshal, doctor, steward, atlas, warden, herald, mason, scribe).
- Given `--project` names a project with no discovered Tier-3 file, when `--write-baseline`
  runs, then the script exits 2 and stderr names the unknown project among the known set.

## Spec Change Log

## Review Triage Log

### 2026-08-11 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 1, medium 1)
- defer: 0
- reject: 9 (medium 1, low 8)
- addressed_findings:
  - `high` `patch` Both reviewers independently found, and I confirmed live via direct reproduction (a real partial checkout with only 1 of 8 projects' gitignored Tier-3 scratch present), that a bare `--write-baseline` run silently REGRESSED the committed baseline from 8 projects to 1, discarding grandfather protection for the other 7 -- defeating the epic's core "grandfathered wholesale" guarantee. Root cause: the bare-mode branch built `merged` directly from `current` (only what's locally discoverable right now) instead of merging with the existing committed file, unlike the `--project`-scoped branch a few lines above it, which already merges. A second, related report (an unreadable Tier-3 directory silently reads as "project skipped" rather than raising) shares the identical root cause and is fixed by the same change -- I verified this empirically (the alternate claim that it crashes with a traceback was reproduced FALSE). Fixed: bare `--write-baseline` now reads the existing committed file first and overlays only the currently-discovered projects' fresh counts (`merged = {**existing, **current}`), exactly mirroring the scoped path's own "merge, never rewrite" principle. Added `test_bare_write_baseline_never_drops_a_previously_stamped_project_it_cannot_currently_see`, which reproduces the exact scenario and pins the fix.
  - `medium` `patch` Both reviewers independently found that `_patched_stamper`'s `str.replace()`-based test technique fails SILENTLY (no exception, original text returned unchanged) if the `REPO_ROOT` line is ever reformatted -- every test would then run against, and potentially overwrite, the real committed `scripts/.deferred-work-baseline.json` instead of the `tmp_path` fixture, undetected. Fixed: the helper now asserts the substitution target was actually present in the source before proceeding.
- Rejected (9): the epic's own "470" figure is stale (live-measured total is 506, growing) -- already explicitly documented and justified in this spec's own Design Notes, which the reviewers could not see (the spec file itself is gitignored Tier-3, invisible to a diff-only review) -- not a defect, `[low]`. No embedded date/timestamp field in the baseline artifact -- the git commit that introduces/updates the file already provides dated provenance, matching the unchallenged, already-shipped `.spec-surface-baseline.json` precedent's own convention of zero embedded metadata -- `[low]`. "Departs from the named precedent's shape (warden's per-id `expires_at`, or spec-surface's per-file hash) without explanation" -- explained at length in this spec's Design Notes (again invisible to a diff-only review); the code docstring's own explanation is adequate for a maintainer who also has the spec -- `[low]`. The aggregate-count shape could theoretically mask a "vanish + new entry appears" swap that cancels out in the count -- investigated: the append-only discipline this design explicitly depends on (verified live, see Boundaries) makes an existing entry vanishing structurally impossible through any normal write path in this repo, and CAP-2's own actually-named mutation test (deleting an id heading, which INCREASES the anonymous count) is correctly caught by the positional-slice design -- `[medium]`, real-sounding but the premise doesn't hold under the verified invariant. Hardcoded per-project counts in the module docstring will go stale after a future scoped re-stamp -- the docstring already frames them as "measured live at authoring time," a point-in-time snapshot, matching this repo's own established docstring convention elsewhere -- `[low]`. No atomic write (a Ctrl-C mid-write could corrupt the file) -- inherited unchanged from the `spec_surface_check.py` precedent this story deliberately mirrors, not a new deviation -- `[low]`. No file locking against concurrent `--project` invocations -- same as above, inherited unchanged from the precedent -- `[low]`. Malformed/corrupted existing baseline JSON raises an unhandled `JSONDecodeError` rather than a clean error -- inherited unchanged from the precedent's identical unguarded `json.loads` call -- `[low]`. `--project` name matching is case-sensitive/untrimmed with no did-you-mean -- matches the precedent's own exact-match behavior, a manually-invoked rare tool -- `[low]`.

### 2026-08-11 — Review pass (repair: bmad-loop deterministic verification failure)
- intent_gap: 0
- bad_spec: 0
- patch: 1 (medium 1)
- defer: 2 (medium 1, low 1)
- reject: 7 (low 7)
- addressed_findings:
  - `high` (verification, not review) The previous session's commit (`05aced7aeb`) left `scripts/deferred_work_baseline.py` and `scripts/.deferred-work-baseline.json` ungoverned under bmad-loop's own S-13.7 spec-surface reconciliation gate (`python scripts/spec_surface_reconcile.py`, one of this story's two deterministic verify commands) -- neither file matched any Spec's `surface:` glob nor an `scripts/spec_surface_allowlist.txt` entry, so `[ungoverned]` FAILed the gate before any code-level review of this diff had even happened. Root cause: the story's own Code Map never named a governance path for the two new files. Fixed by allowlisting both, mirroring the exact precedent this story's own Design Notes already cite (`scripts/spec_surface_check.py`/`scripts/bmad_drift_check.py`/`scripts/spec_surface_reconcile.py` are all allowlisted "mutation-only residual, no DETECTOR marker, no pixi task" tools, not spec-surface-governed) -- confirmed correct by independently re-deriving the `ungoverned`-vs-`drift` code paths in `chain.py` (an allowlist entry clears `ungoverned`; a Spec `surface:`+`.memlog.md` entry is the reconciliation path for `drift` on an already-governed file, a different finding kind not applicable here). Both bmad-loop verify commands green after the fix (`python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`, 842 passed).
  - `medium` `patch` Both reviewers independently found `_anonymous()`'s `path.is_file()` guard (and `_live_state()`'s identical `t3_path.is_file()` guard) silently swallows a `PermissionError` on an unreadable ancestor directory and returns `False`/"no entries" -- directly contradicting the script's own docstring claim of being a "verbatim (in shape)" duplicate of `chain.py::_anonymous`, whose own `_is_file()`/`_probe()` deliberately raise rather than lie, for the exact "confidently wrong" reason `chain.py`'s module docstrings spend paragraphs on. Reproduced live: `Path.is_file()`/`Path.exists()` both return `False` (not raise) when a PARENT directory has no search permission, while `Path.stat()`/`read_text()` raise `PermissionError` for the identical case. Fixed: both guards now `try: path.stat() except FileNotFoundError: return []`/`continue`, so a genuinely-missing Tier-3 file is still silently skipped (per the spec's own I/O matrix), but any other unreadable-path failure now raises loudly instead of under-counting a project's grandfathered backlog. Re-verified: `pytest tests/scripts/test_deferred_work_baseline.py -q` (10 passed, unchanged), `python scripts/deferred_work_baseline.py --write-baseline` (re-stamped, byte-identical output), both bmad-loop verify commands still green.
  - `defer` (2 new ids minted, doctor station, non-mason `DW-FU-{story}` shape) `medium` The backlog's growth from the epic's measured 470 (2026-08-10T19:15) to this story's stamped 506 spans Story 7.1's merge (2026-08-10 21:06:04) with no evidence of whether the growth happened before or after -- the one fact that would show whether 7.1's identity-minting fix is actually holding. Minted `DW-FU-7-2` in doctor's Tier-3 ledger; not patched here (Never clause forbids triaging/wiring the backlog; confirming 7.1's efficacy needs a dedicated investigation Tier-3 entries carry no timestamp field to support directly).
  - `defer` `low` A project already present in the committed baseline whose Tier-3 file later disappears entirely (backlog resolved and file deleted, or a not-yet-backlinked worktree) can never have its count explicitly lowered or zeroed via `--project <slug>`, because the unknown-project check only consults currently-discoverable projects -- the stamped count becomes a permanent ceiling. Minted `DW-FU-7-2-2`; not patched here (speculative edge case that has not occurred in this repo yet, and the Never clause forbids backlog triage -- a fix belongs to Story 7.3 or a dedicated later pass).
  - `reject` (7, all `[low]`) Unguarded `json.loads` on the existing baseline (crashes on malformed JSON) -- the literal `spec_surface_check.py` precedent has the identical unguarded call; already rejected once in the pass above for this exact reasoning. No atomic write / no file locking -- same precedent-inheritance reasoning, already rejected once above. No `isinstance`/shape validation on merged baseline values -- verified live: `spec_surface_check.py`'s own `--write-baseline` merge (`merged = json.loads(...)`) has the identical gap, so this is inherited, not a new deviation. `projects_dir.iterdir()` raising a raw traceback on an unlistable directory -- a loud crash is the accepted, precedented behavior for this class of rare, manually-invoked mutation tool (same tolerance already established for the json.loads/atomic-write rejections). "The duplication targets a Tier-3 code path that doesn't exist in `chain.py` yet, so the 'matches exactly' docstring claim is unverifiable" -- the duplicated function is real, tested, path-agnostic code that behaves identically regardless of which path is passed to it; that Story 7.3 hasn't yet wired `chain.py` to call it against the Tier-3 path is already transparently disclosed in this story's own docstring and Design Notes. No test for the bare-mode "a previously-stamped project's live count decreases" scenario -- the merge is an unconditional key-overwrite with no distinct code path for growth vs. shrinkage; already structurally covered by the existing growth/merge tests. No automated parity/sync test between the duplicated `_ENTRY_RE`/`_ANON_RE`/`_anonymous()` copies and `chain.py`'s originals -- confirmed the literal precedent this story mirrors has no such test either; inherited, not a new deviation.

## Design Notes

**Why a bare per-project INT rather than a richer structure (line numbers, hashes, dates).**
The file's append-only discipline (verified live this pass, see Boundaries) makes position
alone sufficient to distinguish "existed at cutoff" from "new" -- a future comparison is then a
one-line slice (`_anonymous(path)[baseline.get(project, 0):]`), not a lookup. A richer
per-entry scheme would add real complexity for zero correctness benefit under a guarantee this
story independently confirmed holds.

**Why duplicate `_anonymous()` instead of importing `pyforge.doctor.sources.chain`.**
`spec_surface_check.py` already established this convention for the exact same reason
(`scripts/*.py` must run with `python scripts/foo.py` alone, no package install) -- this story
follows the existing precedent rather than introducing a second one.

**Why this spec measures 506, not the epic's "470."** The backlog is a live, growing thing
(measured totals exceed the epic's per-project breakdown in 4 of 8 projects, always upward) --
which is the epic's own argument FOR a dated-cutoff mechanism over a fixed number, not a defect
in this spec. The committed baseline's actual numbers will be whatever is current at the moment
this story executes its last task, not the number written here.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- `git diff --stat` touches only `scripts/deferred_work_baseline.py`,
  `scripts/.deferred-work-baseline.json`, and the new test file -- nothing under
  `pyforge/doctor/sources/` or any pixi.toml task.

## Auto Run Result

Status: done

**Summary.** Prior session's implementation (commit `05aced7aeb`) was functionally complete but
failed bmad-loop's deterministic verification: `python scripts/spec_surface_reconcile.py`
FAILed with `[ungoverned]` on both new files. This resumed session diagnosed and repaired the
gap, ran a review pass on the cumulative diff, patched one real finding, deferred two, and
committed the repair (`183f345b9b`).

**Files changed (this repair pass, on top of the already-committed `05aced7aeb`):**
- `scripts/spec_surface_allowlist.txt` -- added two per-file entries (`deferred_work_baseline.py`,
  `.deferred-work-baseline.json`), mirroring the existing `spec_surface_check.py`/
  `bmad_drift_check.py`/`spec_surface_reconcile.py` "mutation-only residual" allowlist precedent.
  Clears the `ungoverned` FAIL; does not touch any Spec `surface:` or `.memlog.md`.
- `scripts/deferred_work_baseline.py` -- `_anonymous()`/`_live_state()` now distinguish
  "genuinely missing" (`FileNotFoundError`, skip/empty as before) from "present but unreadable"
  (now raises, previously silently read as 0/absent via `Path.is_file()`'s error-swallowing).
- `_bmad-output/projects/pyforge-doctor/implementation-artifacts/deferred-work.md` (Tier-3,
  gitignored) -- two new identified defer entries, `DW-FU-7-2` and `DW-FU-7-2-2`.

**Review findings breakdown (this pass):** patch 1 (medium, applied), defer 2 (medium 1 / low 1,
minted as `DW-FU-7-2` / `DW-FU-7-2-2`), reject 7 (all low, each either already rejected once in
the prior pass for the identical precedent-inheritance reason, or independently confirmed the
literal precedent this story mirrors has the same gap). Full detail in the Review Triage Log
above.

**Follow-up review recommendation:** `false` -- this pass's only patch is a single, small,
well-precedented, fully-verified fix; the governance repair is metadata-only (an allowlist
addition, no logic).

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- `OK: every tracked file governed or allowlisted;
  no drift.` (was `FAIL`, root cause of the resume)
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- 842 passed, 1 skipped
- `python -m pytest tests/scripts/test_deferred_work_baseline.py -q` -- 10 passed
- `pixi run -e pyforge-ci pyforge-doctor-scripts-test` -- 42 passed, 8 skipped
- `python scripts/deferred_work_baseline.py --write-baseline` re-run after the patch -- baseline
  output byte-identical (the fix changes only the unreadable-path branch, never the happy path)
- Both bmad-loop verify commands (`policy.toml`'s `[verify].commands`) confirmed green

**Residual risks:** `python -m pyforge.doctor.sources deferred-work` reports pre-existing
`tier3-only-deferral` FAILs (ids present in Tier-3, not yet promoted to the tracked ledger,
including the two new `DW-FU-7-2*` ids just minted) -- expected and unrelated to this story
(confirmed `pyforge.doctor.sources.chain` is byte-identical between `baseline_revision` and
`final_revision`; the FAILs are a pre-existing, separately-tracked condition, not a regression
this story introduced). The two deferred findings above (7.1-regression-timing question,
vanished-project baseline ceiling) remain open in doctor's Tier-3 ledger for later focused
attention.

