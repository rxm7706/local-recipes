---
title: "Story 47.2: skf-export is proven to accept the foundry skills root"
type: story
created: 2026-09-07
baseline_revision: e2734e550c
status: done
review_loop_iteration: 1
followup_review_recommended: false
context: pyforge-steward
warnings: []
deferred:
  - summary: "SKF has no link-generation step of any kind -- the .claude/skills/ 'generated per-machine links' the cutover target-tree diagram assumes does not exist anywhere in SKF today; a dedicated link-generator (or an SKF feature) must be built before any station's live IDE skill discovery can rely on a skills/stations/ canonical root"
    evidence: "Confirmed empirically (scratch worktree run) and independently re-confirmed by Blind Hunter reading skf-export-skill's full source directly; relayed to spec-python-foundry-cutover's own memlog as a finding for that project to close"
    location: "_bmad/skf/skf-export-skill/ (no file -- an absence, not a bug in an existing file)"
    severity: medium
  - summary: "Changing skills_output_folder alone does not migrate or discover an already-exported package at the OLD root -- SKF's resolution ladder (manifest / active symlink / flat path) has no cross-root fallback, so a real cutover needs an explicit move/re-forge step per already-exported skill, not just the fnd:AD-12 config-key flip"
    evidence: "Empirically confirmed (Run 1 halted exit 3 resolution-failure); independently re-confirmed by Blind Hunter reading load-skill.md's resolution logic directly"
    location: "_bmad/skf/skf-export-skill/references/load-skill.md (resolution ladder)"
    severity: medium
  - summary: "With snippet_skill_root_override left set, a re-exported skill's managed-section root: pointer can silently drift from its package's real new location with no warning from SKF"
    evidence: "Observed live in the scratch run: pyforge-herald's root: pointer stayed at the old .claude/skills/ location after its package moved to skills/stations/..."
    location: "_bmad/skf/skf-export-skill/references/update-context.md (root-rewrite logic, override branch)"
    severity: low
---

# Story 47.2: `skf-export` is proven to accept the foundry skills root

<intent-contract>

## Intent

Actually run `skf-export-skill` (SKF's own real, agent-driven export workflow —
never simulated) against a config pointed at the foundry's planned canonical
skills root (`skills/stations`, per `spec-python-foundry-cutover/cutover.md`'s
target layout), in a throwaway scratch git worktree, and observe — for real —
whether the exported package lands where the cutover spine assumes and
whether anything in SKF generates the `.claude/skills/<x>` "adapter" the
cutover's target tree diagram calls "generated per-machine links" (fnd:AD-19).
Investigation already read every relevant `skf-export-skill` reference file
in this repo's own installed copy (`references/package.md`,
`generate-snippet.md`, `update-context.md`, `preflight-snippet-root-probe.md`)
and found no adapter-generation step anywhere in the workflow: SKF writes the
versioned package under `{skills_output_folder}/{skill}/{version}/{skill}/`
and updates CLAUDE.md/AGENTS.md's managed section with a **context snippet**
(a documentation pointer), never an actual `.claude/skills/<x>/SKILL.md`
runtime file. This story's job is to CONFIRM that reading empirically (the
whole point of "prove," not "assume from re-reading the same prose again"),
then record the precise gap as a `spec-python-foundry-cutover` memlog finding
if confirmed — never silently assume the cutover spine's own claim is simply
true.

Separately, P10's other half — "hand-set keys survive an apply" — is
re-verified against CAP-7's actual restore mechanism (already read:
`_bmad/skf/config.yaml` is one of skf's `config_paths` in the release
catalog, snapshotted before the core installer runs and restored verbatim
after — a live filesystem snapshot, not literally `git checkout`, though
functionally equivalent for a clean tree since the file is git-tracked). The
single fnd:AD-12 declaring key for the foundry's planned re-render approach
(`_bmad/custom/config.toml [modules.skf].skills_output_folder`, confirmed
already present in this repo) is recorded, alongside the observation that
TODAY's mechanism is snapshot-restore, not the fnd:AD-12-target re-render — a
gap between today's mechanism and the foundry's target, recorded, not
built.

## Boundaries & Constraints

- **`_bmad/skf/config.yaml` is NEVER edited in place in the real worktree.**
  All experimentation happens in a scratch `git worktree add` copy (created
  under a temp/scratch path outside this worktree's own tree, removed with
  `git worktree remove` when done). The real file's only touch this story
  makes is a read, to confirm its current `skills_output_folder: .claude/
  skills` value as the "before" baseline.
- **The scratch worktree's own git identity is irrelevant** — it is a
  disposable copy of this same repo (branched from this story's own HEAD)
  used purely as an isolated filesystem sandbox for one experimental export
  run; it is never pushed, never merged, never referenced by any other
  story.
- **`skf-export-skill` is run for real, headless, on exactly ONE small,
  low-risk skill** (not `--all` — a full-fleet export in a scratch copy is
  unnecessary risk/noise for what this story needs to observe). Any
  already-exported, non-deprecated skill already on disk under
  `_bmad/skf/*-skill/` or one of the `skf-*` skill directories works; pick
  the smallest one found (fewest reference files) to keep the run fast.
- **The `--headless` flag is used**, matching this batch's own established
  lesson (Story 46.6) about avoiding interactive-prompt traps — never an
  unattended agent session left hanging on a Confirm Gate.
- **This story does not modify `upgrade.py`, CAP-7's actual restore
  mechanism, or `_bmad/custom/config.toml`.** The Surface line names no
  code file — only `_bmad/skf/config.yaml` (in the scratch copy),
  the scratch worktree itself, and `cutover-readiness.md` G5/P10. Recording
  the fnd:AD-12 declaring key and the snapshot-vs-re-render gap is a FINDING
  (memlog), never an implementation.
- **If SKF genuinely lacks the link-generation step** (the expected,
  investigation-grounded outcome): this is recorded as a
  `spec-python-foundry-cutover` memlog finding, worded as a gap for that
  project to close (build the link-generator, or teach SKF one), never as
  "this story failed" — the AC's own text explicitly names this as one of
  the two valid outcomes ("or the story records precisely which key/option
  skf lacks").
- **P10's own "Owner → story" cell in `cutover-readiness.md` is this story
  (`steward 47.2`)** — recording the finding IS this story's job, already
  named by the checklist; nothing to reassign.

## I/O Matrix

| Input | Behavior |
|---|---|
| Scratch worktree, `_bmad/skf/config.yaml`'s `skills_output_folder` changed to `skills/stations` | The real `_bmad/skf/config.yaml` in this worktree is untouched (confirmed via `git diff` / `git status` in the ORIGINAL worktree after the experiment) |
| `skf-export-skill --headless <one-skill-name>` run in the scratch worktree | Exported package lands at `skills/stations/<skill-name>/<version>/<skill-name>/` (confirmed present); `.export-manifest.json` lands at `skills/stations/.export-manifest.json` |
| CLAUDE.md / AGENTS.md managed sections in the scratch worktree, after the run | Gain a context-snippet row citing the new `skills/stations/...` location — but NO `.claude/skills/<skill-name>/SKILL.md` file is created anywhere by this run (the expected, investigation-grounded finding — confirmed empirically, not assumed) |
| `cutover-readiness.md` G5 | State cell updated: dated, records whether the export-to-custom-root claim held (yes) and whether the link-generation adapter exists (no — recorded as the precise gap) |
| `cutover-readiness.md` P10 | State cell updated: the fnd:AD-12 declaring key named, CAP-7's actual snapshot-restore mechanism confirmed (not re-render), the gap between the two recorded |
| `.memlog.md` (spec-bmad-suite-lifecycle) | One event recording both findings |
| `.memlog.md` (spec-python-foundry-cutover, if it has one — confirm before assuming) | One finding entry naming the missing link-generation step as that project's own gap to close |

</intent-contract>

## Code Map

- **Scratch experiment (not a code change):**
  1. `git worktree add <scratch-path> HEAD` (a detached-or-branched scratch
     copy of the CURRENT worktree's HEAD, created OUTSIDE this worktree's
     own directory tree — e.g. under the scratchpad area).
  2. In the scratch copy: edit `_bmad/skf/config.yaml`'s
     `skills_output_folder` from `.claude/skills` to `skills/stations`
     (leave `snippet_skill_root_override` as-is unless the run's own
     preflight-snippet-root-probe demands a change — record what actually
     happens).
  3. Identify one small, already-exported skf skill on disk to re-export
     (e.g. via the manifest or a flat `SKILL.md` under one of skf's own
     `skf-*/` dirs).
  4. Actually run the `skf-export-skill` workflow, headless, against that
     one skill, in the scratch copy — following the real SKILL.md steps as
     an agent (Load Skill → Package → Generate Snippet → Update Context →
     Token Report → Summary → Health Check), not a simulation.
  5. Inspect the scratch copy's resulting filesystem state: does
     `skills/stations/<skill>/<version>/<skill>/` exist with the expected
     package contents? Does `skills/stations/.export-manifest.json` exist?
     Does anything under `.claude/skills/` in the scratch copy change at
     all? What does the CLAUDE.md/AGENTS.md managed-section diff look like?
  6. Remove the scratch worktree (`git worktree remove`) once findings are
     captured — nothing from it is committed or kept.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/cutover-readiness.md`
  - G5 row: state cell updated with the dated finding.
  - P10 row: state cell updated with the fnd:AD-12 key + snapshot-vs-re-render
    gap.
- `.memlog.md` for `spec-bmad-suite-lifecycle`: one event.
- `spec-python-foundry-cutover`'s own memlog (path confirmed before
  writing — read its directory first): one finding entry, IF the
  link-generation gap is confirmed as expected.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`:
  `47-2-...: backlog` → `done`.

## Tasks & Acceptance

1. **Create the scratch worktree; confirm the real worktree's own
   `_bmad/skf/config.yaml` is never touched.**
   - AC: `git worktree list` shows the scratch copy during the experiment;
     `git status --short` / `git diff -- _bmad/skf/config.yaml` in the
     REAL (this) worktree is empty throughout and after.
2. **Run `skf-export-skill --headless` on one skill in the scratch copy
   with `skills_output_folder: skills/stations`.**
   - AC: the run completes (exit 0, `SKF_EXPORT_RESULT_JSON` with
     `status: "success"`) or, if it halts, the exact halt reason/exit code
     is recorded verbatim — never silently retried with undocumented
     flags.
3. **Inspect and record the real outcome.**
   - AC: `skills/stations/<skill>/<version>/<skill>/SKILL.md` exists in
     the scratch copy (or the AC's alternative: precisely which key/option
     is missing, recorded); the presence or absence of any new
     `.claude/skills/<skill>` file/symlink in the scratch copy is recorded
     as an explicit yes/no with evidence (`find`/`ls` output), never
     assumed from the prose investigation alone.
4. **Record the fnd:AD-12 declaring key and CAP-7's actual mechanism for P10.**
   - AC: `cutover-readiness.md`'s P10 cell names
     `_bmad/custom/config.toml [modules.skf].skills_output_folder`
     verbatim and states plainly that CAP-7 today snapshots/restores
     `_bmad/skf/config.yaml` (not a re-render from that key) — a recorded
     gap, not a claim it's already fixed.
5. **Update `cutover-readiness.md` G5/P10, the memlog(s), and the ledger.**
   - AC: both rows dated; the scratch worktree is removed
     (`git worktree list` no longer shows it); ledger flipped to `done`.

## Spec Change Log

- 2026-09-07: initial draft, written directly (no fork) after reading
  `skf-export-skill`'s full workflow (`SKILL.md` + every stage reference
  file touching `skills_output_folder`/`snippet_skill_root_override`),
  `spec-python-foundry-cutover/cutover.md`'s target-tree diagram (the
  `skills/stations/<station>/` + `.claude/skills/ (generated per-machine
  links, gitignored, fnd:AD-19)` claim), the release catalog's skf
  `config_paths` entry (`_bmad/skf/config.yaml`, snapshot/restore, not
  re-render), and confirming `_bmad/custom/config.toml [modules.skf]
  .skills_output_folder` already exists in this repo (Story 46.2's own
  AD-9 migration wrote it).

## Review Triage Log

Two independent, context-free reviewer subagents ran against the diff (Blind
Hunter + Verification Gap; a deliberate, documented two-reviewer reduction
from the usual four given this story's doc/investigation-only shape, no
source-code changes, and the same low-blast-radius profile Story 47.1
already established this precedent for). 0 findings requiring a patch; 1
documented, accepted epistemic limitation noted by Verification Gap.

- **Blind Hunter**: independently re-verified every empirically-checkable
  claim in the diff against the REAL, currently-installed source (not the
  now-deleted scratch run) — read `skf-export-skill`'s full reference chain
  and every `_bmad/skf/shared/scripts/*.py` helper directly and confirmed
  no code path anywhere creates/symlinks/touches `.claude/skills/<name>`
  (the sole `os.symlink` call, in `skf-update-active-symlink.py`, operates
  exclusively within `{skill_group}/active` under `skills_output_folder`
  itself, never `.claude/skills`); confirmed `load-skill.md`'s resolution
  ladder is genuinely scoped entirely to the current `skills_output_folder`
  value with no cross-root fallback; read `upgrade.py::
  _restore_custom_module_configs` directly and confirmed it does exactly
  `path.write_bytes(before)` per config path, never referencing
  `_bmad/custom/config.toml`; confirmed `[modules.skf].skills_output_folder`
  live content matches the diff's claim verbatim; confirmed no row besides
  P10/G5 changed in `cutover-readiness.md`; confirmed the real
  `_bmad/skf/config.yaml` shows zero drift. No findings.
- **Verification Gap**: independently confirmed Tasks 1, 4, 5 against
  currently-live, re-checkable state (git diff/status, the live
  `[modules.skf]` block, both memlog diffs, the ledger flip, `git worktree
  list` showing zero lingering scratch worktrees). For Tasks 2/3 (the
  specific halt/success details and the "`.claude/skills/` unchanged"
  observation from the now-deleted scratch run), found the story's prose
  specific and internally consistent — not vague — but flagged a genuine,
  **structural, not-actionable** limitation: since the spec's own Boundaries
  explicitly mandate removing the scratch worktree when done (never keeping
  or committing it), there is no surviving transcript/log artifact to
  independently replay those two exact observations after the fact. This is
  an accepted trade-off of the "scratch, then destroy" design this story
  was explicitly told to use, not a fabrication risk or something to fix —
  re-running the whole two-attempt experiment again solely to retain a log
  would be wasted, redundant work for a fact already recorded faithfully at
  the time. No patch applied; recorded here as a known, accepted
  characteristic of investigation stories that use disposable scratch
  environments, for whoever reads this spec later.

Post-review verification: `pixi run -e pyforge-steward pyforge-steward-test`
→ **1180 passed** (unchanged — this story makes no source-code changes).
`git worktree list` confirmed clean (no lingering scratch worktree).

## Design Notes

- **Why the link-generation gap is the EXPECTED finding, not a surprise
  discovered mid-implementation:** every `skf-export-skill` reference file
  that touches the managed-section / context-injection mechanism
  (`generate-snippet.md`, `update-context.md`) describes writing a
  **context snippet** — prose text with a `root:` path pointer — into
  CLAUDE.md/AGENTS.md's managed section. None of them describe creating an
  actual `.claude/skills/<name>/SKILL.md` file, a symlink, or any other
  runtime-discoverable artifact. The cutover spine's own target-tree
  diagram labels `.claude/skills/` as "generated per-machine links" without
  naming WHAT generates them — this story's live run is expected to
  confirm that SKF itself is not that generator, making this a genuine,
  actionable gap for `spec-python-foundry-cutover` to close (build a
  dedicated link-generator, or extend SKF with one), not a step this
  story invents or implements itself.
- **Why the scratch worktree is created OUTSIDE this worktree's own tree,
  not as a subdirectory inside it:** `git worktree add` targeting a path
  inside an already-worktree-isolated checkout risks the same "operating
  on a path the sandbox cannot verify stays inside the worktree" class of
  guard rejection seen earlier in this batch (Story 46.6's home-directory
  studio experiments) if not handled carefully — a sibling temp directory
  (e.g. under the harness's own scratchpad path) keeps the operation
  simple and unambiguous.

## Implementation Notes

Executed 2026-09-07. Scratch worktree created with `git worktree add
<scratchpad>/skf-export-scratch HEAD` (detached at `e2734e550c`, the
spec's own `baseline_revision`), removed with `git worktree remove
--force` when done — `git worktree list` no longer shows it. `git
status --short` / `git diff -- _bmad/skf/config.yaml` in THIS (real)
worktree were empty before, during, and after (verified three times).

**Two runs, not one — recorded transparently.** Task 2's Code Map step
said "identify one small, already-exported skf skill on disk to
re-export." Picked `pyforge-herald` (0 references, smallest SKILL.md of
the 7 manifest-listed `pyforge-*` packages — no `skf-*`-named skill
in `.claude/skills/skf-*/` carries a `metadata.json`, so none is a valid
export target; only the 7 already-exported `pyforge-*` stack packages
qualify). Running the workflow literally as configured surfaced a real
gate *before* the link-generation question could even be observed, so a
second, clearly-labeled run was added to complete the investigation
without masking the first result — this is not "silently retried with
undocumented flags" (boundary 6/AC2): the two runs have different,
explicitly-stated preconditions and both outcomes are reported in full.

**Run 1 (literal, as-instructed precondition) — HALT, exit 3,
`resolution-failure`.** With `skills_output_folder: skills/stations` and
`pyforge-herald` referenced by name at its existing `.claude/skills/`
location, `load-skill.md` §2 resolves `{resolved_skill_package}` purely
against the *current* `skills_output_folder` — manifest, then `active`
symlink, then flat path, all checked only under `skills/stations/`.
Confirmed empirically (not inferred): `test -f
skills/stations/.export-manifest.json` → absent; `test -L
skills/stations/pyforge-herald/active` → absent; `test -f
skills/stations/pyforge-herald/SKILL.md` → absent. All three resolution
rungs miss, so `{resolved_skill_package}` never exists and the "Required
Files (hard halt if missing)" clause fires — SKILL.md's own Exit Codes
table maps this exact case ("step 1 §2 — a named skill's required
artifacts are missing") to exit 3 / `resolution-failure`. Headless error
envelope (constructed per `references/result-envelope.md`, this
branch's shape is fully deterministic from the prose — no agent
judgment call was needed to fill it in):
`SKF_EXPORT_RESULT_JSON: {"status":"error","skills":["pyforge-herald"],"context_files_updated":[],"manifest_path":null,"headless_decisions":[],"exit_code":3,"halt_reason":"resolution-failure"}`.
**This is a genuine, previously-unnamed finding**: flipping the fnd:AD-12
declaring key alone does not migrate or even make discoverable an
already-exported package that physically lives at the old root — there
is no cross-root fallback anywhere in `version-paths.md`'s documented
resolution ladder.

**Run 2 (skill staged flat at the new root, to isolate the
link-generation question) — SUCCESS, exit 0.** Copied
`.claude/skills/pyforge-herald/0.1.0/pyforge-herald/{SKILL.md,
metadata.json,context-snippet.md,provenance-map.json}` flat to
`skills/stations/pyforge-herald/` — a real, documented SKF scenario
("Migration: Flat to Versioned" in `knowledge/version-paths.md`), not a
fabricated shortcut. Performed that migration by hand exactly per its
7-step recipe (create versioned dir, move the 4 files, create the
`active -> 0.1.0` symlink), then ran every subsequent stage for real,
invoking the actual scripts rather than narrating them:
`skf-validate-output.py --export-gate` → `PASS` / `READY`;
`skf-count-tokens.py` → context-snippet 130 tokens, package total 1601;
`skf-rebuild-managed-sections.py orphan-detect` → correctly found the 6
sibling `pyforge-*` rows (atlas/doctor/marshal/scribe/steward/warden) as
orphans against this run's single-skill exported set, headless default
(b) Preserve verbatim applied; `skf-rebuild-managed-sections.py replace`
→ rewrote CLAUDE.md and AGENTS.md's managed sections for real (Case 3);
`skf-manifest-ops.py set` then `read` → confirmed
`skills/stations/.export-manifest.json` written with `pyforge-herald`
`active_version: 0.1.0`.

**Task 3 findings, all with direct filesystem/git evidence, not
assumption:**
- (a) **Package landed exactly where the target layout assumes**:
  `skills/stations/pyforge-herald/0.1.0/pyforge-herald/SKILL.md` exists
  (`find`/`test -f` both confirm); `skills/stations/.export-manifest.json`
  exists with the correct v2 shape.
- (b) **Nothing under `.claude/skills/` changed — confirmed empirically,
  not merely re-asserted from the prose investigation**:
  `git status --short -- .claude/skills/` and `git diff --stat --
  .claude/skills/` in the scratch worktree were both byte-empty after
  the full run. The only changes anywhere in the scratch worktree were
  `AGENTS.md` (modified), `CLAUDE.md` (modified), `_bmad/skf/config.yaml`
  (our own deliberate edit), and the new untracked `skills/` tree. No
  script under `_bmad/skf/shared/scripts/*.py` (33 scripts inventoried)
  performs any symlink/adapter creation; none of `package.md`,
  `generate-snippet.md`, or `update-context.md` name `.claude/skills`
  as a write target anywhere in their MANDATORY SEQUENCE — only as a
  *string value* (`snippet_skill_root_override`) embedded in generated
  text. **The link-generation gap is confirmed, not assumed.**
- (c) **CLAUDE.md/AGENTS.md diff**: `git diff -- CLAUDE.md` / `AGENTS.md`
  in the scratch worktree shows exactly one changed line each — the
  `<!-- SKF:BEGIN updated:2026-08-26 -->` → `updated:2026-09-07` marker
  timestamp. All 4017 bytes of managed-section body are byte-identical
  to before. Notably, `pyforge-herald`'s own `root:` line still reads
  `.claude/skills/pyforge-herald/` — **stale**, since its package now
  lives at `skills/stations/pyforge-herald/...` — because
  `snippet_skill_root_override` was correctly left untouched per this
  story's own instruction (`generate-snippet.md` §2.7 uses the override
  as `{skill_root}` unconditionally when set, bypassing IDE mapping
  entirely) and the `preflight-snippet-root-probe.md` mismatch gate is
  *skipped entirely* whenever the override is already set (`load-skill.md`
  §1b), so nothing ever inspected or flagged the drift. This is a live,
  concrete instance of the exact adapter gap fnd:AD-19 assumes away, not a
  hypothetical.

**Task 4 — re-verified against live code, not re-stated from the spec's
own prose.** Read (never edited) `upgrade.py` in this worktree:
`_snapshot_custom_module_configs` (line ~1656) records pre-installer
bytes of every catalog `config_paths` entry; `_restore_custom_module_configs`
(line ~1707) writes `path.write_bytes(before)` — a verbatim byte
restore, never a read of, or derivation from, `_bmad/custom/config.toml`.
`grep` confirms `_bmad/skf/config.yaml` is a `skf` module `config_paths`
entry in `src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/6.12.0.yaml:154`.
`_bmad/custom/config.toml`'s `[modules.skf]` table (this worktree, real
file) carries `skills_output_folder = "{project-root}/.claude/skills"` —
present, confirmed, but **not yet wired to anything**: no code path
reads this key to regenerate `_bmad/skf/config.yaml`. The two files are
independent today; CAP-7 preserves whatever bytes were already in
`config.yaml` verbatim, regardless of what config.toml says. This is the
snapshot-vs-re-render gap fnd:AD-12 targets — recorded, not built (zero
`upgrade.py` edits this story, per boundary 9).

**Health-check step (the real terminal step, not skipped).** Reflecting
honestly on the two runs per `shared/health-check.md`'s own
anti-hallucination rules, three genuine findings were actually
encountered (not fabricated to appear thorough): (1) Run 1's halt is a
`gap` — the flat-to-versioned migration path is documented, but a
"skill exists at a *different*, no-longer-configured root" scenario has
no documented path at all; (2) the stale `root:` pointer after a
`skills_output_folder` change while `snippet_skill_root_override` stays
fixed is a `gap` — nothing warns that the two settings can drift; (3)
the health-check's own step 4 "User Review Gate" is the only Confirm
Gate in this entire workflow with no stated headless default (every
other gate in `load-skill.md`/`update-context.md` explicitly says
"Headless [default C]" or similar) — a `friction` finding about this
very workflow's own instructions. Per this story's boundaries (no
external actions, no PRs, nothing beyond the named Surface) these were
**not** submitted live to `armelhbobdad/bmad-module-skill-forge` — no
operator consent was sought or given for a third-party GitHub write, and
the gate's own missing headless default makes "submit" an unsafe
default action to invent. Recorded here instead for a human to decide
whether to file them upstream.

**Deviation from the intent-contract's own text:** none — the
"expected, investigation-grounded outcome" (no adapter-generation step
anywhere in SKF) is confirmed exactly as predicted. The Run-1 halt and
the stale-override interaction are *additions* the investigation's
static read did not surface, not contradictions of it; both are
recorded as new findings per boundary 14 rather than smoothed over.

**Ledger / memlog / readiness-doc writes** (all in THIS worktree, never
the scratch copy): `cutover-readiness.md` G5 and P10 cells updated
(dated 2026-09-07, both marked resolved with the findings above);
`spec-bmad-suite-lifecycle/.memlog.md` gained one Story 47.2 event (and
its `updated:` frontmatter bumped); `spec-python-foundry-cutover/.memlog.md`
gained one relayed finding entry (it has its own `.memlog.md` — confirmed
present before writing, per the Code Map's own instruction to check
first); `sprint-status-ledger.yaml`'s `47-2-...` row flipped
`backlog` → `done`.

**Test suite.** `pixi run -e pyforge-steward pyforge-steward-test` from
THIS worktree's root: **1180 passed**, 0 failed — this story made zero
source-code changes, so this is a clean re-confirmation, not a
regression check against new code.

## Auto Run Result

Status: done
Blocking condition: none

Implementation delivered all 5 tasks via a real, headless `skf-export-skill`
run in a throwaway scratch worktree (cleanly removed afterward). Confirmed
the export root claim holds (`skills/stations/<x>/` genuinely accepted) and
uncovered three genuine, previously-unnamed gaps: SKF has no link-generation
step at all (medium, relayed to spec-python-foundry-cutover), the resolution
ladder has no cross-root fallback for already-exported skills (medium), and
`snippet_skill_root_override` can silently drift from a migrated package's
real location (low). A 2-reviewer pass (Blind Hunter + Verification Gap,
documented reduction given the doc-only, zero-source-code-change shape)
independently re-verified every checkable claim against the real, currently-
installed source and found zero findings requiring a patch. `cutover-
readiness.md` G5 and P10 both resolved with dated findings; the real
`_bmad/skf/config.yaml` in this worktree shows zero drift throughout. Final
suite: 1180 passed (unchanged, zero source-code changes).
