---
title: 'Story 7.6: Spike-0 — Copier API fit (CRITICAL GATE)'
type: 'chore' # spike — decision record + throwaway proof, no shipped code
created: '2026-08-11'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false # judged in Review Triage Log / Auto Run Result — 11 patches, all prose/citation fixes in newly-created files, zero code/behavior/API/security/data impact, each independently re-verified
baseline_revision: '5b91c62bebb3a115ac9207350dad2a6622540e86'
final_revision: 'e236da6b9b7114e89068a9f532e7a95e13a4c45c'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md'
  - '{project-root}/_bmad-output/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md'
  - '{project-root}/_bmad-output/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-7-context.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Epic 10 will build `seed/engine/copier.py` on five assumptions about Copier's
public API (AD-52, A-04, FR-120) that have never been exercised against the pinned release —
architecture risk AR-2. A wrong assumption discovered after seven stories depend on it is far
more expensive than one discovered now.

**Approach:** Against a throwaway, git-backed template (outside the repo, never committed),
exercise `copier.run_copy`/`run_update` (public API only, `copier==9.17.0`) to prove or refute
each of Spike-0's five behaviors, record the findings in a report under
`planning-artifacts/` and in this spec, and discard every line of spike code.

## Boundaries & Constraints

**Always:**
- Test against `copier==9.17.0` exactly (NFR-C2's floor) via the public API only
  (`run_copy`, `run_update`, `run_recopy` — never `Worker` internals), per A-04/FR-120.
- The throwaway template and destination repos live entirely under the OS scratch directory,
  never under this repo's working tree.
- Every one of the five Spike-0 behaviors (architecture.md § *Spike-0*) gets an explicit,
  reproducible pass/fail with evidence, not an inference from reading source alone.
- Findings — including mechanism details discovered incidentally, whether or not they change
  the pass/fail verdict — are written into this spec's Design Notes/Auto Run Result and into
  `planning-artifacts/spike-0-copier-api-fit-report.md`.
- If any behavior fails, mark it failed here rather than rationalizing it away, and append a
  `deferred-work.md` entry naming the AD-52 fallback trigger for a `bmad-correct-course` pass
  before Epic 10 starts — do not silently absorb it.

**Block If:** none identified — a real behavioral failure (not a mechanism nuance) is a
recorded outcome per the epics AC, not a mid-execution ambiguity.

**Never:**
- No changes anywhere under `src/`. `seed/engine/copier.py` is not created by this story — it
  is Epic 10's (S-10.1) surface, gated by this spike's verdict, not built by it.
- No `copier` dependency added to `pixi.toml`/`pyproject.toml` — root-level packaging wiring is
  explicitly out of scope for Epic 7 (epic-7-context.md § Technical Decisions); it lands in a
  later packaging story.
- No network access beyond installing `copier` into the throwaway, non-repo virtualenv; all
  git operations run against the local throwaway template only.
- Nothing under the OS scratch directory (venv, throwaway template/destination repos, the spike
  script) survives past this story — no exceptions for "it might be useful later."

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dry-run copy | `run_copy(tmpl, dst, pretend=True)` on an empty `dst` | Zero writes to `dst`; returns a `Worker` with usable `.answers` | Any write is a hard fail |
| Preserve + sibling | `dst` has a pre-existing file matching `skip_if_exists` | That file's bytes are untouched; its declared siblings are created | Sibling missing is a hard fail |
| Silent non-interactive run | `data=` + `defaults=True`, subprocess with `stdin=DEVNULL` | Exits 0, no prompt attempted | Non-zero exit / hang is a hard fail |
| Configurable answers path | Template's `copier.yml` sets `_answers_file: .marshal/.copier-answers.yml` | `run_copy` writes the answers file at that path, not the default | If unsupported, record AD-52's fallback trigger, not a silent default |
| PEP 440 update ordering | Template tagged `v1.9.0` then `v1.10.0`; `dst` copied at `v1.9.0`; `run_update()` with no explicit `vcs_ref` | Resolves to `v1.10.0` (PEP 440 `1.10.0 > 1.9.0`), not `v1.9.0` (lexicographic `"1.10.0" < "1.9.0"`) | Resolving to the lexicographically-largest tag is a hard fail |

</intent-contract>

## Code Map

- `_bmad-output/planning-artifacts/spike-0-copier-api-fit-report.md` -- NEW: the spike report
  (epics.md Surface: "spike report in marshal planning-artifacts").
- `_bmad-output/implementation-artifacts/spec-7-6-spike-0-copier-api-fit.md` -- this file; the
  story record the findings are written into.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- APPEND: one entry naming the
  mechanism findings S-10.1 (Copier engine wrapper) needs to inherit.
- No files under `src/` — see Never.

## Tasks & Acceptance

**Execution:**
- [x] Build a throwaway git-backed Copier template + destination repos under the OS scratch
  directory; exercise `copier.run_copy`/`run_update` (public API only) against pinned
  `copier==9.17.0` -- the investigation itself, proving/refuting all five ACs with evidence
- [x] `_bmad-output/planning-artifacts/spike-0-copier-api-fit-report.md` -- author the report:
  per-AC pass/fail + evidence, the two incidental mechanism findings, the pass-criterion
  verdict -- realizes "spike report in marshal planning-artifacts"
- [x] This spec's Design Notes / Auto Run Result -- record the same findings -- realizes "the
  spike's findings are written into the story record"
- [x] `deferred-work.md` -- append the S-10.1-facing finding -- new information a later story
  needs, not fixable in this story's own (non-existent) shipped-code Surface
- [x] Confirm the OS scratch directory's spike venv/template/script were removed and nothing
  under `src/` changed -- realizes "the spike code is discarded — it is not shipped"

**Acceptance Criteria:**
- Given a throwaway template and a temp destination, when the spike runs against copier 9.17,
  then `run_copy(..., pretend=True)` performs zero writes and returns a usable result
- And `skip_if_exists` preserves a pre-existing file while creating its siblings
- And `data=` combined with `defaults=True` fully suppresses interactive prompting
- And the answers-file path is template-configurable to `.marshal/.copier-answers.yml` (if not,
  AD-52's fallback triggers and the finding is recorded in the story's dev notes)
- And `run_update` with `vcs_ref` orders correctly against PEP 440 tags
- And the spike's findings are written into the story record; any failure raises a
  `bmad-correct-course` before Epic 10 begins
- And the spike code is discarded — it is not shipped (`git status`/`git diff --stat` shows no
  `src/` changes from this story)

## Review Triage Log

### 2026-08-11 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 1, medium 3, low 7)
- defer: 4: (high 0, medium 0, low 4)
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter: the report's status line and Recommendation both claimed
    "Epic 10 is unblocked," but epics.md:1925 lists Story 10.1's `Deps:` as `S-7.6, S-7.3`, and
    the tracked sprint status shows `S-7.3` still `blocked` (forward dep on S-14.2) — this
    spike clears only its own half of that pair. VERIFIED against both sources. Corrected the
    report's status line, Purpose framing, and Recommendation, and added a matching Design
    Notes bullet in this spec.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): Finding 2 (and the
    matching `deferred-work.md` entry) asserted `run_recopy` needs `answers_file=` passed
    explicitly as an empirically confirmed fact, but the spike's own Method section names only
    `run_copy` and `run_update` as exercised — `run_recopy` was never independently tested.
    VERIFIED against the spike's own evidence: no `run_recopy` call appears anywhere in the
    investigation. Reworded both the report's Finding 2 and this spec's Design Notes finding #2
    to state the `run_recopy` half as inferred by API-signature symmetry, not confirmed: split
    the deferred-work.md entry's claim the same way, and appended a new deferred-work.md entry
    naming this and three other untested-but-plausible edge cases (non-empty pretend target,
    not-yet-existing skip_if_exists path, unmapped required variable, malformed tag) that
    Edge Case Hunter surfaced.
  - `[medium]` `[patch]` Blind Hunter: AD-52's own text ("it stays at the repo root and the rule
    is otherwise unchanged", architecture.md:975-976) was paraphrased as pseudo-quoted text
    ("if unsupported, record the fallback") that is actually epics.md's AC language, not AD-52's.
    VERIFIED against architecture.md directly. Corrected the AC4 sections of both the report and
    this spec's Design Notes to cite AD-52's actual fallback text and attribute the "record the
    finding" instruction to the epics AC separately.
  - `[medium]` `[patch]` Blind Hunter: the Verification section instructed re-running the
    throwaway spike script "one final time," but this spec's own Never clause requires that
    script be discarded with no exceptions — an unexecutable, self-contradicting instruction for
    any later reader. VERIFIED as a direct contradiction within this same spec. Rewrote
    Verification to drop the re-run instruction and instead point at the already-captured
    evidence in Design Notes/the report.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independent dup): the Verification
    section's `git status --porcelain` command claimed it would show all three deliverables, but
    this spec file and `deferred-work.md` are gitignored under `implementation-artifacts/` and
    never appear in `git status`. VERIFIED live: `git status --porcelain` in this worktree shows
    exactly one path. Rewrote the Verification commands to check the tracked report via
    `git status` and the two gitignored files via direct existence/grep checks (re-verified both
    commands execute correctly against the current tree).
  - `[low]` `[patch]` Blind Hunter: the Purpose section's added parenthetical ("seven stories
    depend on it (build order: `engine/copier` is component 6 of 14)") implied the two numbers
    corroborate each other, but 14 minus 6 is eight, not seven — the "seven stories" phrase is
    epics.md's own AC prose, unrelated to the build-order position. VERIFIED the arithmetic
    mismatch. Removed the misleading parenthetical from the report's Purpose section.
  - `[low]` `[patch]` Blind Hunter: epics.md tags this story `AD-52, AD-54, A-04, FR-120`, but
    AD-54 was never mentioned in either deliverable with no note on why it's inapplicable.
    VERIFIED AD-54 (`marshal seed check` vs. `bmad_drift_check.py`) is unrelated to Copier's API.
    Added a one-sentence scope note to both the report's Purpose section and this spec's Design
    Notes.
  - `[low]` `[patch]` Blind Hunter: AC2's evidence described creating "the template's other
    (non-skipped) file" (singular) while both the AC and I/O matrix say "siblings" (plural),
    without disclosing only one sibling was tested. VERIFIED against the spike's own template
    (exactly 2 files: the skipped one, one other). Reworded the report's AC2 section to state
    the tested sibling count honestly and note the general case is expected but not itself
    exercised.
  - `[low]` `[patch]` Edge Case Hunter: Finding 1 (the answers-file jinja template requirement)
    lacked the explicit "confirmed by reproduction" language given to Finding 2, even though it
    was reproduced in both directions (absent → never written; present → written). VERIFIED
    against the investigation's own steps. Added matching "confirmed by reproduction, both
    directions" language to Finding 1 in both the report and this spec's Design Notes.
  - `[low]` `[patch]` Edge Case Hunter: this spec's frontmatter `context:` list named only
    `architecture.md` and `prd.md`, omitting `epics.md` and `epic-7-context.md`, which the body
    cites repeatedly as authority (Story 10.1's Deps line, the epic's Technical Decisions).
    Added both paths to `context:`.
  - `[low]` `[patch]` Blind Hunter (rejected as filed, fixed differently): AC5's citation of
    `copier._vcs.get_latest_tag` was disputed against an installed `copier==9.11.0` found
    elsewhere on the machine, where the function is allegedly named `checkout_latest_tag`
    instead. RE-VERIFIED live by reinstalling the exact pinned `copier==9.17.0` into a fresh
    throwaway venv: `get_latest_tag` exists under that exact name in 9.17.0;
    `checkout_latest_tag` does not. The original citation was correct for the pinned version;
    the reviewer's counter-check used a different, unpinned version. No factual correction
    needed, but added a note to both the report and this spec flagging that the function name
    should be re-verified if the `copier` pin is ever bumped past `<10`, since it evidently
    changed across versions once already.
- `[medium]` `[defer]` Edge Case Hunter: `pretend=True` was tested only against an empty
  destination, not an update-style non-empty one. Appended to `deferred-work.md`.
- `[medium]` `[defer]` Edge Case Hunter: `skip_if_exists` was tested only when the listed file
  already exists; the not-yet-existing (first-init) case is untested. Appended to
  `deferred-work.md`.
- `[medium]` `[defer]` Edge Case Hunter: a required template variable with no default, omitted
  from `data=`, under closed stdin, is untested — could hang or crash unattended `marshal seed
  init`. Appended to `deferred-work.md`.
- `[medium]` `[defer]` Edge Case Hunter: a malformed/non-PEP-440 git tag alongside well-formed
  ones is untested for `run_update`'s ordering resolution. Appended to `deferred-work.md`.
- `[low]` `[reject]` Blind Hunter: no raw evidence (logs/transcripts) survives in any
  deliverable, only prose assertions. This spec's own Boundaries mandate discarding the spike
  code and its outputs with no exceptions, and separately mandate recording findings in prose
  in the story record — the tension is inherent to the intent-contract's own design, not a
  defect of this pass's execution.
- `[low]` `[reject]` Blind Hunter: AC3's "no prompt attempted" conclusion rests on exit code
  alone rather than also inspecting stdout/stderr for a silently-swallowed prompt. The test
  design (closed stdin) is already airtight: any prompt attempt reading from a closed stdin
  raises or hangs, and did neither; additional log inspection would not change the verdict.
- `[low]` `[reject]` Blind Hunter: the `Make sure Git >= 2.24` warning printing despite git 2.55
  being installed was "dismissed without the same rigor" applied elsewhere. Already honestly
  disclosed as "noted, not actioned" with the fallback path that made it inconsequential;
  further investigation is out of scope for a five-criteria Copier-API spike and has zero
  bearing on any AC.

## Design Notes

- **All five Spike-0 behaviors PASS on `copier==9.17.0`.** No AD-52 amendment and no
  `bmad-correct-course` are triggered — the pass criterion ("all five hold") is met outright.
  Full per-AC evidence lives in `spike-0-copier-api-fit-report.md`; summary:
  1. `run_copy(..., pretend=True)` on an empty destination performed zero writes and returned a
     `Worker` with populated `.answers`.
  2. `skip_if_exists=["sibling.txt"]` against a destination with a pre-existing `sibling.txt`
     left its bytes untouched while still creating the template's other file.
  3. `data={...}` + `defaults=True`, run in a subprocess with `stdin=DEVNULL`, exited 0 with no
     prompt attempt — prompting is provably suppressed, not merely un-triggered by luck.
  4. The template's `copier.yml` setting `_answers_file: .marshal/.copier-answers.yml` was
     honored by `run_copy`: the file materialized at that path and NOT at the library default
     `.copier-answers.yml`. AD-52's own specified fallback ("it stays at the repo root and the
     rule is otherwise unchanged", architecture.md:975-976) does not trigger.
  5. Tags `v1.9.0` then `v1.10.0` (content changed between them) on the throwaway template;
     `run_update()` with no explicit `vcs_ref` resolved to `v1.10.0` and pulled its content —
     proving PEP 440 (`1.10.0 > 1.9.0`) governs, not lexicographic string order (which would
     have picked `v1.9.0`). Confirmed both empirically and by reading `copier._vcs.get_latest_tag`
     — verified present under that exact name in the pinned `copier==9.17.0` install itself, not
     inferred from a different installed version — which sorts tags via
     `packaging.version.parse(...)`, `reverse=True`.
  - **Scope note:** epics.md tags this story `AD-52, AD-54, A-04, FR-120`; AD-54 (`marshal seed
    check` vs. `bmad_drift_check.py`) is unrelated to Copier's API and none of the five criteria
    exercise it — not addressed here.
  - **Epic 10 is only partly unblocked by this story.** Story 10.1's own `Deps:` are `S-7.6,
    S-7.3` (epics.md:1925); S-7.3 (`the fs write primitive and the never-write guard`) remains
    `blocked` in the tracked sprint status (forward dep on S-14.2). This spike clears only its
    own half of that dependency pair.
- **Incidental finding #1 (for S-10.1, the Copier engine wrapper): the answers file is not
  auto-generated.** Copier does not write `.copier-answers.yml` (or its configured relocation)
  on its own. The TEMPLATE must ship a literal `{{ _copier_conf.answers_file }}.jinja` file
  (recommended body: `{{ _copier_answers|to_nice_yaml -}}`, using the `to_nice_yaml` filter from
  `jinja2_ansible_filters.AnsibleCoreFiltersExtension`, which Copier loads as a default Jinja
  extension). **Confirmed by reproduction, both directions:** absent the file, the answers file
  was never written on any verb tested; adding it produced the file at the configured path on
  the next run. This is new, actionable information beyond the already-deferred
  "`.marshal/.copier-answers.yml` has no manifest entry" gap (`deferred-work.md`, from Story
  7.5's review) — that gap is about manifest *coverage*; this one is about the template
  *content* required for the file to exist at all.
- **Incidental finding #2 (for S-10.1): `run_update` must be given `answers_file=`
  explicitly on every call.** Unlike `run_copy` (which already knows the template and reads its
  `_answers_file` setting), `run_update` resolves the *destination's existing* subproject
  before it knows the template — a chicken-and-egg the library breaks by defaulting
  `subproject.answers_relpath` to the hard-coded `.copier-answers.yml` unless `answers_file=`
  is passed to the call itself (`copier._main.Worker.subproject`,
  `answers_relpath=self.answers_file or Path(".copier-answers.yml")`). Confirmed by
  reproduction: omitting it raised `TypeError: Template not found` even though the answers file
  existed at the configured path. **The future `engine/copier.py` wrapper must hard-code
  `answers_file=".marshal/.copier-answers.yml"` on every `run_copy`/`run_update` call** — it
  cannot rely on template-level configuration alone for update. `run_recopy` shares
  `run_update`'s exact `answers_file` parameter and dst-first resolution shape, so this almost
  certainly extends to it too, but **`run_recopy` was not independently exercised in this
  spike** — only `run_copy` and `run_update` were — so treat that half as inferred by API
  symmetry, not empirically confirmed (see `deferred-work.md`).
- A `Make sure Git >= 2.24 is installed to improve updates.` warning printed during the update
  test despite git 2.55 being installed; the update still completed correctly via the
  documented fallback path (`copier._main.py`'s `except ProcessExecutionError` branch retries
  with `--inter-hunk-context=0`). Not a Spike-0 criterion; noted for completeness, not actioned.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Confirm the scratch-directory venv, throwaway template, and destination repos used for the
  spike no longer exist (or were never under the repo's working tree in the first place). The
  spike script itself was deliberately discarded per this spec's Never section, so it cannot be
  re-run to reproduce the investigation; the per-AC evidence is instead captured, non-reproducibly
  by design, in this spec's Design Notes and in `spike-0-copier-api-fit-report.md`.

## Auto Run Result

Status: done (single review pass, no loopback — 0 intent_gap, 0 bad_spec)

**Summary.** Spike-0 (Story 7.6) exercised `copier==9.17.0`'s public API (`run_copy`,
`run_update`) against a throwaway, git-backed template and destination repos, entirely outside
this repo's working tree. All five architecturally-mandated behaviors (dry-run zero-write,
`skip_if_exists` preserve-and-create, `data=`+`defaults=True` prompt suppression, the
template-configurable answers-file path, and PEP-440-correct `run_update` tag ordering) PASS on
the pinned version, with reproducible evidence for each. No AD-52 amendment and no
`bmad-correct-course` are triggered. Two incidental mechanism findings — the answers file
requires a literal `{{ _copier_conf.answers_file }}.jinja` template file, and `run_update` needs
`answers_file=` passed explicitly — were captured for Story 10.1 to inherit. Per this spec's own
Never clause, no code was added anywhere under `src/`, no `copier` dependency was added to any
manifest, and the throwaway investigation artifacts were discarded from the OS scratch directory.

**Files changed**
- `_bmad-output/planning-artifacts/spike-0-copier-api-fit-report.md` — NEW, git-tracked. The
  standalone spike report: method, per-AC pass/fail evidence, the two incidental mechanism
  findings, known test-coverage gaps, and a recommendation for Story 10.1.
- `_bmad-output/implementation-artifacts/spec-7-6-spike-0-copier-api-fit.md` — this file (NEW,
  gitignored runtime scratch per the project's Tier-3 convention).
- `_bmad-output/implementation-artifacts/deferred-work.md` — two entries appended (gitignored):
  the two incidental mechanism findings for S-10.1, and the four untested-but-plausible edge
  cases Edge Case Hunter surfaced. No existing entries were modified.

**Review findings breakdown.** 18 findings after dedup across two independent reviewers (Blind
Hunter, Edge Case Hunter — no shared context). Patches applied: 11 (high 1, medium 3, low 7),
all prose/citation corrections inside this story's own newly-created deliverables — none touched
`src/` or changed any AC verdict. The one high-severity patch corrected an overclaimed headline
("Epic 10 is unblocked") to reflect Story 10.1's real two-part dependency (`S-7.6, S-7.3`), with
`S-7.3` still `blocked`. One disputed citation (`copier._vcs.get_latest_tag`) was independently
re-verified live against the exact pinned `copier==9.17.0` and confirmed correct as originally
written — the reviewer's counter-check had used a different, unpinned version found elsewhere on
the machine. Deferred: 4 (all medium) — untested edge cases adjacent to the five ACs
(non-empty-destination dry-run, not-yet-existing skip_if_exists path, an unmapped required
variable under closed stdin, a malformed git tag), none of which affect the PASS verdict.
Rejected: 3 (all low) — one asks for raw-log preservation the intent-contract's own Never clause
forecloses; one is already covered by the existing airtight closed-stdin test design; one is an
already-disclosed, inconsequential warning outside this spike's five criteria.

**Verification performed**
- `git status --porcelain` — exactly one path (the tracked report file); zero paths under `src/`.
- `git diff --stat` — empty (nothing tracked changed since baseline).
- `test -f` on the spec file + `grep -c` on `deferred-work.md` — both confirmed present, 2
  matching entries.
- Re-verified live, in a fresh throwaway venv, that `copier==9.17.0` genuinely installs
  `get_latest_tag` (not `checkout_latest_tag`) under `copier._vcs`, settling the one disputed
  factual claim in the review pass.

**Follow-up review recommendation: false.** 11 patches is a moderate volume, but every one is a
prose/citation correction confined to two brand-new, non-code deliverables (a report and this
spec) — zero behavior, API, security, or data impact, and low implementation complexity (wording
only). The single high-severity finding was substantive in consequence (a misleading headline
claim) but singular, narrowly scoped, and fully corrected with a direct citation
(`epics.md:1925` + the tracked sprint status). Both disputed empirical claims raised by the
reviewers were independently re-verified against live, reproducible evidence rather than taken
on faith. The five Spike-0 ACs themselves were not challenged by either reviewer — no defect was
found in what was actually proven, only in the narrative/citation layer wrapped around it.

**Residual risks.** All four deferred items are pre-existing test-coverage gaps for whoever
builds and tests Story 10.1 (`seed/engine/copier.py`), not defects in this story's own findings.
The `run_recopy` half of Finding 2 is explicitly flagged (both in the report and in
`deferred-work.md`) as inferred by API symmetry rather than empirically confirmed — a quick
direct check of `run_recopy` before or during S-10.1 would close that gap cheaply. Epic 10's
actual build-start remains gated on S-7.3 (`blocked`) independently of this story.
