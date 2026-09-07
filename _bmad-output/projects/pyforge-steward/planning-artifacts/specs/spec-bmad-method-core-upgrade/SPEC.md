---
spec: bmad-method-core-upgrade
# CORRECTED 2026-09-06: a follow-up review pass flipped this to `shipped`
# on its own judgment, against an explicit instruction to leave the status
# decision to the operator. Reverted to `in-progress` by the operator: all 8
# CAPs are implemented (CAP-1..5 exercised live 2026-09-06; CAP-6 Story 14.6
# 0286066638, CAP-7 Story 14.7 196b8a8d2a + d7935753fc, CAP-8 Story 14.8
# 297689f8d6 + d6758c7978 + 2f915b2049 — all unit-tested with injected
# runners), but CAP-6..8's own success signal — a live apply-time re-run
# against a FUTURE bmad-method release with zero improvised recoveries — has
# not happened; the owning Dream is still `specified`, not `realized`; and
# the cited spec-mcp-era-isolation precedent for "success signal pending,
# call it shipped anyway" does not exist in this tree to verify. Flip to
# `shipped` when the next bmad-method release apply exercises CAP-6..8 live.
status: in-progress
owner-dream: docs/dreams/bmad-method-core-upgrade.md
surface: []   # upgrade.py + data/bmad_core_releases/ are governed by spec-pyforge-steward's surface; not double-governed here
companions:
  - failure-modes.md
  - customization-inventory.md
sources:
  - ../../../../../../docs/dreams/bmad-method-core-upgrade.md
assumptions:
  - "conda-forge bmad-method (pixi-provisioned) remains the install channel. The
    installer's `--action update -y` is safe to re-run ONLY for core/bmm and only
    when driven with `--directory <repo>` and an explicit `--modules` list; it is
    not idempotent for custom modules, module config, or in-place skill edits
    (falsified live 2026-09-06 — failure-modes.md traps 12–16)."
  - "6.11's four-layer TOML config is 'the migration, not the cutover' (release
    notes verbatim; unchanged at 6.12) — `_bmad/bmm/config.yaml` still ships and the
    planning-artifacts symlink pattern still works; CAP-1 must flag the eventual
    TOML cutover release."
open_questions:
  - "Should doctor's ambient drift extend to the SelfExplainML bmad-suite
    packages? bmad-loop lagged 0.9.0→0.11.0 with zero ambient signal until a
    human checked (2026-08-21). Doctor-side scope — relayed 2026-09-06 to doctor
    Story 20.1 (spec-bmad-suite-lifecycle); doctor maps 7 of 13 members today."
  - "Where does bmad-method read remembered `[modules.skf]` answers from —
    `_bmad/config.toml` or the module `config.yaml`? Empirical at the next apply;
    the custom-layer pins exist in `_bmad/custom/config.toml` (C7/C17 done)."
  # Answered 2026-09-06 (memlog): Q2 @next → report-only rehearsal (steward 46.10);
  # Q3 skf truth = conda-packaged 2.1.0 == tag v2.1.0 (pin, 46.7); Q5 skf stays a
  # registered custom module (bmad-help routing for 15 skills).
---

# SPEC — The installed BMAD-METHOD core upgrades repeatably, not by heroics

## Why

The fleet has no repeatable way to take a new BMAD-METHOD release into this
repo's already-installed core. Both upgrades ever performed were manual
one-offs: 6.6.0→6.10.0 (bmad-loop-adoption W1) and 6.10.0→6.11.0 (2026-08-21,
the session this spec is grounded in) — the second re-hit the first's traps,
including the same custom-surface clobber. Doctor's shipped drift detector
(Stories 10.1/10.2) reports "you're behind" ambiently, but nothing can act on
it. Ownership was resolved 2026-08-15 by a two-pass investigation recorded in
the Dream: **steward** owns the mutating apply half (marshal is ruled out by
its own installer-owned boundary; genesis-installer verifies floors and never
installs; `bmad-module-provisioning`'s "never absorb" constraint was narrowed
to first-install, carving this territory out by name). The first
steward-driven apply (6.11.0→6.12.0, 2026-09-06) ran CAP-1..5 end to end and
still improvised five recoveries — the installer no-ops on a closed stdin,
deletes a cached custom module, regenerates module config and in-repo skill
edits, and its regenerated user layer halted every rendering skill — which is
what CAP-6..8 close.

## Capabilities

- **CAP-1 — Pre-flight diff (report-only).** *Intent:* given the installed
  manifest and a target release, report skill adds/removes/renames (shim
  disposition + `removals.txt` deletions), upstream-touched files the repo has
  locally modified, `_bmad/custom/**` overrides that stop applying (the
  legacy-name unattended-halt trap), and new hard prerequisites (e.g. `uv`).
  *Success:* run against the 6.10.0→6.11.0 pair, it retrodicts the 2026-08-21
  findings (companion, § Traps).
- **CAP-2 — Deliberate, reviewable apply.** *Intent:* wrap
  `bmad-method install --action update -y` non-interactively: branch/snapshot
  first, never a silent overwrite of `_bmad/custom/**`, installer diff landed
  for review — never applied blind in place. *Success:* a clean run lands the
  installer diff on a review branch with the custom-surface checklist executed.
- **CAP-3 — Custom-surface reconciliation.** *Intent:* after apply, detect
  clobbered repo-custom surfaces — `resolve_config.py`'s multi-project layers
  5/6 is the named recurring case, clobbered in BOTH manual upgrades — and
  re-apply or flag them. *Success:* post-apply, `bmad-switch --current` and a
  `BMAD_ACTIVE_PROJECT` override both resolve the six layers; the installer's
  `.bak` is accounted for.
- **CAP-4 — Downstream pin fan-out report (report-only).** *Intent:* enumerate
  every pin site the release moves — root `pixi.toml` floors, marshal's
  pyproject + package `pixi.toml` + `HARNESS_VERSION_RANGE_TEXT` + seed
  manifest/drift-test map, loop-home hook relays — and report moved vs. not.
  *Success:* names exactly the sites the 2026-08-21 session had to touch, none
  discovered later by red tests.
- **CAP-5 — Post-apply verification gate.** *Intent:* run the repo's own gates
  (bmad-drift-check integrity, CFE skill meta-tests, `bmad-loop validate` per
  loop home including the `init` relay refresh) and report one verdict.
  *Success:* reproduces the 2026-08-21 checklist (8/8 loop homes validate
  clean) in one command.
- **CAP-6 — Non-interactive installer drive.** *Intent:* the apply drives the
  installer on purpose, not by luck — `--directory <repo>`, `--modules <every
  module the installed manifest lists>` (core, bmm, each `source: custom`
  module), stdin closed, node and `bmad-method` resolved from the repo's pixi
  env when absent from PATH — and an exit-0 run that changed nothing is a
  refusal, never a green. *Success:* a re-run of the 2026-09-06 apply from a
  clean tree lands the 6.12 installer diff with no wrapper script.
- **CAP-7 — Custom-module awareness.** *Intent:* every `source: custom` module
  in `_bmad/_config/manifest.yaml` (today skf) is selected for the core apply;
  its config files (named in the release catalog) are snapshotted before and
  restored after; its own installer runs after the core apply so its module
  tree, undeclared skills and shared resources land coherently; an optional
  catalog pin stops the channel-`next` cache drift. *Success:* after apply the
  module's skill dirs equal its packaged source and its config equals the
  pre-apply bytes plus the installer's own appended keys; the report names each
  restored file.
- **CAP-8 — Local-customization scan and re-apply.** *Intent:* before apply,
  every installer-owned file is compared against the cached package of the
  installed version and the customized ones are listed in the CAP-1 report (the
  Dream's own first when-real bullet, which CAP-1 had narrowed to
  marker-carrying scripts); after apply each is re-applied by three-way merge
  onto the new upstream copy, clean merges written, conflicts flagged with the
  hunk kept beside the report. `resolve_config.py` takes the same path — the
  old→new upstream delta is replayed on the restored copy, not discarded.
  *Success:* the 2026-09-06 seven-file case re-applies with six clean merges
  and one flagged conflict (step-01 `done` routing).

- **CAP-9 — Deliberate shim retirement (`--no-shims`)** *(added 2026-09-06,
  spec-bmad-suite-lifecycle CAP-10; corrected 2026-09-06, Story 30.5 —
  see below)*. *Intent:* the apply can retire every deprecation shim on
  purpose — `--no-shims` on the installer argv after `--modules`, the
  pre-flight names each shim to retire (21 at 6.12.0), a same-version run is
  accepted as a retirement run, and the flag is refused while a legacy-name
  custom file exists (trap 2). *Success:* the manifest reads
  `installShims: false`, the shim rows leave `skill-manifest.csv`, CAP-7 and
  CAP-8 run on the same apply, `prove-landed` validates 8/8 (Story 14.9).
  **Correction (2026-09-06, found during Story 30.5):** the original Intent
  also refused `--no-shims` "while the marshal harness / any rendered
  loop-home policy still emits `bmad-dev-auto`" — this premise is FALSE,
  verified directly against the installed `bmad_loop` 0.11.1 package source
  (`bmad_loop/policy.py`). `DevPolicy.skill` is a PERMANENT internal adapter
  discriminator (`DEV_SKILLS = {"bmad-dev-auto"}`, hard-validated by
  `PolicyError` on any other value) — it is not a "which skill name is
  current" field, and the skill actually invoked is resolved separately at
  runtime from what is on disk (`Engine._dev_skill()` /
  `install.dev_primitive_or_default`), independent of this field. Every real
  loop-home's `policy.toml` (and the vendored `harness_bmadloop.py` template
  that renders it) will ALWAYS emit this literal, forever, by design — a
  refusal keyed on finding it provides no real signal about `--no-shims`
  readiness and would refuse every retirement attempt permanently. This
  clause is REMOVED: the harness-template / loop-home-policy check
  (`_shim_retirement_blockers` / `refuse_shim_retirement_not_ready`) is
  deleted from `upgrade.py`. The sole pre-apply refusal for `--no-shims`
  remains the pre-existing, unconditional legacy-custom-name check (trap 2,
  `refuse_legacy_custom`), which is unaffected by this correction.

## Constraints

- Never silently overwrite `_bmad/custom/**` — clobber-without-surfacing is
  worse than no upgrade path (the Dream's own top constraint).
- The multi-project marker/symlinks survive an upgrade untouched; the tool
  never calls `bmad-switch` and verifies artifact placement by physical path.
- Refuse or warn before an unattended run when legacy-name customization files
  exist (`_bmad/custom/bmad-dev-auto.toml` etc.) — the 6.11 shim halts instead
  of forwarding on them.
- The upstream installer stays the only writer of `_bmad/bmm/**` and
  `_bmad/core/**` — steward wraps it, never reimplements it.
- Foreign-station surfaces (marshal pin sites, doctor detectors) are
  **reported, never edited** — owners act on the report.
- Runs from the repo's pixi env (installer, `uv`, node all resolve there;
  nothing global).
- A local customization is never dropped silently: a three-way conflict is
  flagged with its hunk, never resolved by taking upstream; an exit-0 apply that
  changed nothing is a refusal (both learned 2026-09-06).

## Non-goals

- Ambient staleness detection — doctor's `bmad-method-version-drift` (shipped,
  10.1/10.2).
- Module keep/drop triage — `one-front-door`'s open question.
- bmad-suite conda-recipe refresh + SelfExplainML channel publishing — the CFE
  factory flow (the 2026-08-21 suite bumps ran there; companion § Suite orbit).
- Editing foreign-station pin sites.
- First-install of adjacent modules — `bmad-module-provisioning` (shipped).

## Success signal

The 6.11.0→6.12.0 apply (2026-09-06) went from "doctor reports behind" to
"installed core current, custom surfaces verified, gates green" through CAP-1..5
but improvised five recoveries (failure-modes.md traps 12–16). The next release
goes through CAP-6..8 with none: no wrapper script, no hand restore of skf, no
hand merge of skill edits, and `render_skill.py` renders on the first try. CAP-1
pointed at the 6.11.0→6.12.0 pair retrodicts traps 12–16 the way it retrodicts
the 2026-08-21 session against 6.10.0→6.11.0.
