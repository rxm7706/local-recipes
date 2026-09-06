# Release cadence — one runbook per BMAD-METHOD release

Companion of `spec-bmad-suite-lifecycle` (CAP-8). Orders the three per-release chains that already
exist (doctor `bmad-method-version-drift`, steward `bmad-method-core-upgrade`, marshal
`bmad-611-era-alignment`) plus the suite refresh and the status flips, so the next release needs no
improvised step. Grounded in the three live upgrades (6.6→6.10, 6.10→6.11, 6.11→6.12) and their
failure-modes catalog (traps 1–16).

## Trigger

`pixi run -e local-recipes bmad-method-version-drift-check` reports `bmad-method-upstream-drift:
warn` (doctor Epic 10), or `steward suite pipeline-truth` names a member behind upstream (doctor
Epic 14/15 relays). Both are ambient, warn-only; nothing acts on them without an operator go.

## Steps (owner → verb → gate)

1. **Doctor — detect.** `bmad-method-version-drift-check`; `steward suite pipeline-truth`
   (network, fail-open). Record the target version and which suite members moved.
2. **Steward — catalog.** Author `data/bmad_core_releases/<target>.yaml` from the **unpacked
   conda package** (never the release page): `skill_renames`, `removals`, `upstream_touched_paths`,
   `legacy_custom_names`, `hard_prerequisites`, `custom_modules` (skf, pinned). Force-add past the
   `data/` ignore rule.
3. **Steward — pre-flight (report-only).** `steward upgrade bmad-core --target <v>
   --package-root <unpacked> --installed-package-root <cached installed>`: shim disposition,
   removals, upstream-touched files, legacy-custom halts, prerequisites, **local customizations**
   (CAP-8 byte-diff scan) — every drifted file must already be under a spec `surface:`.
4. **Steward — apply.** Clean tree, `--apply --branch steward/bmad-core-upgrade-<v>`; the apply
   passes `--directory <repo> --modules <every manifest module>` with stdin closed, refuses a
   zero-diff exit 0, snapshots/restores custom-module configs, runs skf's own installer after the
   core, re-applies local customizations by three-way merge (conflicts left as
   `.customization-conflict` siblings). Delete `_bmad-output/projects/cap3-probe/` and
   `_bmad/scripts/resolve_config.py.bak` before committing.
5. **Steward — prove-landed.** `steward upgrade prove-landed`: drift-integrity via the pixi task,
   CFE meta-tests, `bmad-loop init` + `validate` per loop home (8/8), `render_skill.py` renders on
   the first try (config pins at the installer's key paths).
6. **Marshal — era round.** Open a round of CAPs on `spec-bmad-611-era-alignment` (one round per
   shift, IDs never reused): retired-ID guard follows the new shim roster, `persistent_facts` /
   customization hooks re-checked, living docs re-grounded (`architecture-bmad-infra.md`
   `source_pin`), bmad-loop skill copies re-diffed (meta-test 30.4), policy knobs re-checked.
   Decompose as a new marshal epic; every apply passes `--no-shims` from 2026-09-06 on.
7. **Mason — suite refresh.** For each moved member: `steward suite advance` (tag or HEAD mode)
   through the CFE factory flow → local green build → operator `anaconda upload` →
   `generate-bmad-suite` regenerates the metapackage CalVer → pixi floor bumps
   (`pixi-version-check` / `bump-pixi-version`) → `environment.yaml` regenerated. `pixi.toml`
   edits need a memlog line + scoped `spec_surface_check.py --write-baseline --spec` on each of
   the six blanket-glob specs.
8. **Steward — flips.** Memlog `(event)` on each Spec whose CAPs shipped; SPEC `status:` lines;
   Dream `status:` + Realization log; dreams README rows; `customization-inventory.md` rows;
   `spec-bmad-method-core-upgrade` moves to `shipped` only when CAP-6..8 ran live against a real
   release with zero improvised recoveries.
9. **Steward — record.** Session memory entry; `failure-modes.md` gains any new trap; this
   runbook gains the step that was missing.

## The `@next` rehearsal (optional, report-only)

npm dist-tag `next` carried `6.12.1-next.0` on 2026-09-06. Rehearse in a throwaway worktree, never
merged: `--installer` pointed at `npx bmad-method@next`, `--package-root` at the unpacked next
tarball, `--installed-package-root` at the cached installed package; plant one conflicting local
edit in an installer-owned skill file (exercises CAP-8's conflict path) and strip `node` from
`PATH` (exercises CAP-6's pixi-bin fallback). Read the report; append findings to the
core-upgrade memlog; delete the worktree. This answers the Spec's `@next` open question empirically
and never counts as the live proof that flips the core-upgrade status.

## Watches that change this runbook

- TOML cutover (`_bmad/bmm/config.yaml` retired) — kills the multi-project planning-artifacts
  symlink; step 4 must halt and re-plan.
- `bmad-ticket` tree in a tagged release — retires `sprint-status.yaml`; a new marshal Dream.
- v7 — the shims are already gone here; the guard tuple stays until upstream removes the ids.
