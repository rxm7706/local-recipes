# Release cadence — one runbook per BMAD-METHOD release

Companion of `spec-bmad-suite-lifecycle` (CAP-8). Orders the three per-release chains that already
exist (doctor `bmad-method-version-drift`, steward `bmad-method-core-upgrade`, marshal
`bmad-611-era-alignment`) plus the suite refresh and the status flips, so the next release follows only named steps below. Grounded in the three live upgrades (6.6→6.10, 6.10→6.11, 6.11→6.12) and their
failure-modes catalog (traps 1–16).

## Trigger

`pixi run -e local-recipes bmad-method-version-drift-check` reports `bmad-method-upstream-drift:
warn` (doctor Epic 10), or `steward suite pipeline-truth` names a member behind upstream (doctor
Epic 14/15 relays). Both are ambient, warn-only; nothing acts on them without an operator go.

## Steps (owner → verb → gate)

1. **Doctor — detect.** `bmad-method-version-drift-check`; `steward suite pipeline-truth`
   (network, fail-open). Record the target version and which suite members moved.

   **Verified pass (6.12.0, 2026-09-06):** owner **doctor** |
   `pixi run -e local-recipes bmad-method-version-drift-check` | exit **0** (warn:
   `bmad-method-upstream-drift`) |
   evidence: operator go before `ab52117795` catalog commit.

2. **Steward — catalog.** Author `data/bmad_core_releases/<target>.yaml` from the **unpacked
   conda package** (never the release page): `skill_renames`, `removals`, `upstream_touched_paths`,
   `legacy_custom_names`, `hard_prerequisites`, `custom_modules` (skf, pinned). Force-add past the
   `data/` ignore rule.

   **Verified pass (6.12.0, 2026-09-06):** owner **steward** |
   authored `src/pyforge/steward/data/bmad_core_releases/6.12.0.yaml` from the unpacked conda
   package | exit **0** (git commit) |
   evidence: commit `ab52117795` ("6.12.0 bmad-core release catalog for CAP-1 pre-flight").

3. **Steward — pre-flight (report-only).** `steward upgrade bmad-core --target <v>
   --package-root <unpacked> --installed-package-root <cached installed>`: shim disposition,
   removals, upstream-touched files, legacy-custom halts, prerequisites, **local customizations**
   (CAP-8 byte-diff scan) — every drifted file must already be under a spec `surface:`.

   **Verified pass (6.12.0, 2026-09-06):** owner **steward** |
   `pixi run -e pyforge-steward pyforge steward upgrade bmad-core --target 6.12.0 --repo-root . --installed-package-root <cached-6.11.0-unpacked>` (report-only; no `--apply`) | exit **0** |
   evidence: Story 14.8 memlog — CAP-8 pre-flight named all seven `customization-inventory.md`
   row C5 files; `git status --porcelain` identical before/after.

4. **Steward — apply.** Clean tree, `--apply --branch steward/bmad-core-upgrade-<v>`; the apply
   passes `--directory <repo> --modules <every manifest module>` with stdin closed, refuses a
   zero-diff exit 0, snapshots/restores custom-module configs, runs skf's own installer after the
   core, re-applies local customizations by three-way merge (conflicts left as
   `.customization-conflict` siblings). Delete `_bmad-output/projects/cap3-probe/` and
   `_bmad/scripts/resolve_config.py.bak` before committing.

   **Verified pass (6.12.0, 2026-09-06):** owner **steward** |
   `pixi run -e pyforge-steward pyforge steward upgrade bmad-core --target 6.12.0 --apply --branch steward/bmad-core-upgrade-6.12.0 --repo-root . --package-root <unpacked-6.12.0> --installed-package-root <cached-6.11.0-unpacked>` | exit **0** (branch landed for review) |
   evidence: commit `4fa185be56` ("upgrade BMAD Method 6.11.0 -> 6.12.0 core+bmm via steward
   upgrade bmad-core").

   **Verified pass (--no-shims retirement, 6.12.0, 2026-09-07):** owner **steward** |
   same command with `--no-shims` appended (Story 14.9 / CAP-9) | exit **0** |
   evidence: commit `e7b5d6d05e`; `_bmad/_config/manifest.yaml` reads `installShims: false`.

5. **Steward — prove-landed.** `steward upgrade prove-landed`: drift-integrity via the pixi task,
   CFE meta-tests, `bmad-loop init` + `validate` per loop home (8/8), `render_skill.py` renders on
   the first try (config pins at the installer's key paths).

   **Verified pass (6.12.0, 2026-09-06):** owner **steward** |
   `pixi run -e pyforge-steward pyforge steward upgrade prove-landed --repo-root .` | exit **0**
   (8/8 loop homes validate; drift-integrity via `pixi run -e local-recipes bmad-drift-check`) |
   evidence: Story 14.5 shipped CAP-5; core-upgrade memlog `(note)` 2026-09-06 on prove-landed
   gaps (env/uv follow-ups) closed in CAP-5 amendments same session.

6. **Marshal — era round.** Open a round of CAPs on `spec-bmad-611-era-alignment` (one round per
   shift, IDs never reused): retired-ID guard follows the new shim roster, `persistent_facts` /
   customization hooks re-checked, living docs re-grounded (`architecture-bmad-infra.md`
   `source_pin`), bmad-loop skill copies re-diffed (meta-test 30.4), policy knobs re-checked.
   Decompose as a new marshal epic; every apply passes `--no-shims` from 2026-09-06 on.

   **Verified pass (6.12 era tail, 2026-09-06/07):** owner **marshal** |
   Stories 30.1–30.5 (`pixi run -e pyforge-marshal pyforge-marshal-test` green per story) | exit
   **0** per story verification |
   evidence: marshal ledger keys 30-1 through 30-5 `done`; harness template now emits
   `bmad-build-auto`; guard tuple widened for 21 shim ids.

7. **Mason — suite refresh.** For each moved member: `steward suite advance` (tag or HEAD mode)
   through the CFE factory flow → local green build → operator `anaconda upload` →
   `generate-bmad-suite` regenerates the metapackage CalVer → pixi floor bumps
   (`pixi-version-check` / `bump-pixi-version`) → `environment.yaml` regenerated. `pixi.toml`
   edits need a memlog line + scoped `spec_surface_check.py --write-baseline --spec` on each of
   the six blanket-glob specs.

   **Verified pass (6.12 suite wave, 2026-09-06/07):** owner **mason** (factory) + **steward**
   (pipeline) |
   `pixi run -e pyforge-steward pyforge steward suite pipeline-truth --json` (before/after) and
   per-member `steward suite advance` where stale (Stories 46.2–46.9, mason 14.1) | exit **0** per
   story verification |
   evidence: adoption-register § 1 regenerated from live pipeline-truth (Story 46.9); eval-quality
   `__win` variant landed (mason 14.1).

8. **Steward — flips.** Memlog `(event)` on each Spec whose CAPs shipped; SPEC `status:` lines;
   Dream `status:` + Realization log; dreams README rows; `customization-inventory.md` rows;
   `spec-bmad-method-core-upgrade` moves to `shipped` only when CAP-6..8 ran live against a real
   release with zero hand recoveries.

   **Verified pass (6.12 era, 2026-09-06/09):** owner **steward** |
   memlog `(event)` lines on `spec-bmad-method-core-upgrade`, `spec-bmad-suite-lifecycle`, and
   station relay Specs; ledger sync via `pixi run -e local-recipes sprint-ledger-sync -- --project
   pyforge-steward` | exit **0** |
   evidence: core-upgrade memlog events 2026-09-06 (CAP-6..9 land); **note:** core-upgrade stays
   `in-progress` until the *next* release applies with zero hand recoveries (AD-7) — this step does
   not flip it on the 6.12 apply alone.

9. **Steward — record.** Session memory entry; `failure-modes.md` gains any new trap; this
   runbook gains the step that was missing.

   **Verified pass (6.12.0, 2026-09-06):** owner **steward** |
   `failure-modes.md` traps 12–16 appended from live apply recoveries; `customization-inventory.md`
   rows refreshed; team-memory / session notes per core-upgrade memlog | exit **0** (docs committed)
   |
   evidence: core-upgrade memlog `(correction)` 2026-09-06 traps 12–15; trap 16 from Story 14.8
   live pre-flight.

## The `@next` rehearsal (optional, report-only)

npm dist-tag `next` carried `6.12.1-next.0` on 2026-09-06. Rehearse in a throwaway worktree, never
merged. The recipe below matches `NEXT_REHEARSAL_ARGV` in
`src/shared/packages/pyforge-steward/tests/unit/test_upgrade_next_rehearsal.py` (Story 14.10) —
token-for-token, placeholders shown in angle brackets.

```text
upgrade bmad-core \
  --target 6.12.1-next.0 \
  --apply \
  --repo-root <throwaway-worktree> \
  --installer "npx bmad-method@next" \
  --installed-package-root <cached-6.12.0-unpacked> \
  --package-root <unpacked-next-tarball> \
  --catalog-dir <fixture-or-authored-catalog-dir> \
  --branch rehearsal/next-cap6-cap8
```

Plant one conflicting local edit in an installer-owned skill file (exercises CAP-8's conflict path)
and strip `node` from `PATH` (exercises CAP-6's pixi-bin fallback). Read the report; append findings
to the core-upgrade memlog; delete the worktree.

**Verified pass (fixture rehearsal, 2026-09-10):** owner **steward** |
`pixi run -e pyforge-steward pyforge-steward-test -- -k next_rehearsal -q` | exit **0** (1 passed)
|
evidence: Story 14.10 `test_next_rehearsal_cap6_cap8_cap7_report_only`; core-upgrade memlog
`(event)` 2026-09-10.

**This rehearsal is report-only fixture proof — not live proof.** It does **not** flip
`spec-bmad-method-core-upgrade` to `shipped` (AD-7: only a real future release through CAP-6..8
with zero hand recoveries counts as live proof).

## Watches that change this runbook

- TOML cutover (`_bmad/bmm/config.yaml` retired) — kills the multi-project planning-artifacts
  symlink; step 4 must halt and re-plan.
- `bmad-ticket` tree in a tagged release — retires `sprint-status.yaml`; a new marshal Dream.
- v7 — the shims are already gone here; the guard tuple stays until upstream removes the ids.
