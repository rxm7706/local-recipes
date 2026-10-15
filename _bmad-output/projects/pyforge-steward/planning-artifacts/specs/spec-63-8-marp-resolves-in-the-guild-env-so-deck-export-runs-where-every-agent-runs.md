---
title: "63.8: `marp` resolves in the Guild env, so `deck-export` runs where every agent runs"
type: 'fix'
created: '2026-10-14'
status: 'done'
baseline_revision: '846d8383f5b4a1f86cbb09f6fd8ae8616b34950f'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-63-6-no-station-code-assumes-the-local-recipes-environment-at-runtime.md
  - pixi.toml
  - scripts/deck_export.py
  - tests/scripts/test_deck_export.py
  - docs/how-to/presentation-deck.md
  - src/shared/packages/pyforge-steward/tests/meta/test_no_station_assumes_local_recipes.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `deck-export` cannot run in the environment every agent runs. Story 63.1 moved the Guild tasks into
`[feature.guild-tasks.tasks]` so they run under `-e pyforge-guild`, the session default, and Story 63.6 moved
`deck-export`, `deck-facts` and `deck-trio` there with their `pyforge-herald` import. `deck-export` then runs the
`marp` binary, and `marp-cli` is declared only in `[feature.local-recipes.dependencies]`. Line numbers are at
`846d8383f5`.

- **The gap.** `[feature.pyforge-guild.dependencies]` (`pixi.toml` :864-:924) carries no `marp-cli`;
  `[feature.local-recipes.dependencies]` does (:2314, `marp-cli = ">=4.2.3"`, with the note that conda-forge's
  feedstock tops out there on nodejs 22/24 builds, and that 4.5.0 needs nodejs 26 and a libabseil the a2a-sdk /
  protobuf chain cannot take). The Guild env's `bin/` has no `marp`; `local-recipes`'s does.
- **Who hits it.** `scripts/deck_export.py` `run_marp` (:103-:111) calls `shutil.which("marp")` and, finding nothing,
  exits 1 with `'marp' not on PATH — run via: pixi run -e local-recipes deck-export ...`. herald's `deck pull`,
  `deck sync-all` and the deck pipeline shell the task as `pixi run -e pyforge-guild deck-export <slug>` (herald
  25.1), so under the Guild env every export fails at the first `marp` call. The hint's form, `pixi run -e
  local-recipes <guild task>`, is the one `docs/governance/guild-roster.json`'s `session_denials` refuses as a
  Guild-task / local-recipes mix-up, so a session cannot follow it.
- **The workaround.** The deck-family currency sweep of 2026-10-14 ran every export with
  `PATH="$PWD/.pixi/envs/local-recipes/bin:$PATH"` prepended by hand.
- **The stale lines.** The `deck-export`, `deck-facts` and `deck-trio` task descriptions (`pixi.toml` :1349, :1354,
  :1358), `scripts/deck_export.py`'s docstring (:17-:20) and hint (:108), and `docs/how-to/presentation-deck.md`'s
  Pixi note (:31-:33) and § Generation (:566-:581) all still say `-e local-recipes`.

**Evidence, measured on this host:**
- At `846d8383f5`: `.pixi/envs/pyforge-guild/bin/marp` does not exist and `.pixi/envs/local-recipes/bin/marp` does;
  `pixi run -e pyforge-guild deck-export <slug>` exits 1 with the hint above (verified by the operator the same day).
- With `marp-cli = ">=4.2.3"` added to `[feature.pyforge-guild.dependencies]`: `pixi lock` exits 0 and adds
  `marp-cli 4.2.3` to the four environments that compose the Guild feature (`pyforge-guild`, `default`,
  `pyforge-foundry-full`, `pyforge-foundry-full-stack`) on every platform each solves. On `linux-64` nothing else
  moves (nodejs was already 24.21.0 through `codegraph`). On `win-64` and `osx-arm64` the Guild env's nodejs moves
  26.10.0 → 24.21.0, because conda-forge's `marp-cli` builds are nodejs 22/24, and playwright re-solves 1.63.0 →
  1.64.0 and pnpm re-solves to its nodejs-24 build; `pyforge-foundry-full` on `win-64` moves the same way.
  `pixi install --frozen -e pyforge-guild` exits 0. `pixi run --frozen -e pyforge-guild marp --version` prints
  `@marp-team/marp-cli v4.2.3` and exits 0. `pixi run --frozen -e pyforge-guild deck-export pyforge-scribe` exits 0
  with no `PATH` prefix, regenerating the three artifacts: the standalone HTML byte-identical, the two PPTX files
  and three `.stamp.json` sidecars changed (restored with `git checkout -- presentations/pyforge-scribe`).
- `environment.yaml` is exported from `[feature.build]` (`pixi project export conda-environment -e build`), so the
  pin does not change it: the re-export is byte-identical.

**Approach:**
- **The pin.** `marp-cli = ">=4.2.3"` joins `[feature.pyforge-guild.dependencies]`, beside `pptxgenjs-plus`, with a
  comment naming this story, the task that needs it, the same floor as the `local-recipes` site and the same
  nodejs-26 note. The `local-recipes` line stays as it is. Both sites bump together once the ecosystem gap closes.
- **The lock.** `pixi lock` regenerates `pixi.lock`; the manifest is edited by hand (never `pixi add` / `pixi
  update`, which the session hook refuses).
- **The usage lines.** Every usage line for a Guild task reads `-e pyforge-guild`: the three task descriptions,
  the `guild-tasks` banner (which now names the `marp` dependency), the script's docstring and `run_marp` hint, and
  the deck how-to's Pixi note and § Generation (its three `pixi run -e local-recipes marp` commands).
- **The pins on the fix.** A steward meta test, `tests/meta/test_marp_in_guild_env_story_63_8.py`, parses
  `pixi.toml` and asserts (1) `marp-cli` is a `[feature.pyforge-guild.dependencies]` member at the `local-recipes`
  floor, (2) every `[feature.guild-tasks.tasks]` task whose cmd or description names `marp` (today: `deck-export`)
  resolves it from the Guild feature, and (3) no `guild-tasks` description carries a `pixi run -e local-recipes
  <guild task>` usage line (the hook's own trigger form; `sbom-laptop-gate`'s "Never -e local-recipes" and
  `pr-preflight-lanes`' back-compat note are not usage lines and still pass). `tests/scripts/test_deck_export.py`
  gains `test_run_marp_hint_names_the_guild_env`: with `shutil.which` returning nothing, `run_marp` exits with a
  message naming `pixi run -e pyforge-guild deck-export` and never `local-recipes`.
- **The derived files.** `docs/reference/environments.md` and `docs/how-to/pixi-tasks.md` regenerate through their
  `docs-*` tasks (and `docs/map.yaml`'s stamps with them); the measured env matrix in
  `docs/dreams/pyforge-unifying-strategy.md` regenerates through `scripts/pixi_env_matrix.py --update` (it was
  already stale against the `846d8383f5` lock; `bmad-drift` warns on it); `environment.yaml` is re-exported and is
  unchanged; `llms-full-check` stays clean (`marp-cli` was already catalogued).
- **Unchanged:** the `local-recipes` floor and note, every other dependency in the Guild feature, the task names and
  commands, `scripts/deck_export.py`'s behaviour with `marp` present, the deck pipeline's shell-out, and the hook.

**Rejected:**
- **A `PATH` prefix in the task's `env`** (`PATH = ".pixi/envs/local-recipes/bin:..."`). It would make a Guild task
  depend on a 10 GB environment that does not exist at runtime (CAP-152), which is the defect Story 63.6 closed.
- **Moving `deck-export` back to `[feature.local-recipes.tasks]`.** Tasks move, never duplicate (CAP-5), and
  herald's pipeline shells it from the Guild env by contract (herald 25.1).
- **Bumping to `marp-cli` 4.5.0 on SelfExplainML.** Its nodejs-26 build forces a libabseil that the
  `pyforge-foundry-full` union (a2a-sdk / protobuf, libabseil ~20260107) cannot take; the `local-recipes` note
  already records this, and the Guild's nodejs 24 pin (codegraph, pptxgenjs-plus) points the same way.
- **Editing the herald story specs and Spec companions that cite `pixi run -e local-recipes deck-…`** (herald
  Stories 2.1, 20.2, 20.4, 20.6, 20.14, 21.6, 21.8, 21.12; `bridge-protocol.md`, `facts-ledger.md`). Those are
  landed verification records and herald-owned Spec text; `scripts/deck_facts.py` and `scripts/deck_trio.py` also
  carry docstring and emitted usage lines (`deck_facts.py` writes one into every `facts.yaml` header). Recorded here
  for herald, not changed by this story.

Ledger key: `63-8-marp-resolves-in-the-guild-env-so-deck-export-runs-where-every-agent-runs`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-5: `pyforge-guild` is the default environment for every agent,
  and the Guild tasks live in it (Story 63.1). CAP-152: no station code assumes `local-recipes` at runtime, so
  `deck-export` moved into `guild-tasks` with its `pyforge-herald` import (Story 63.6). This story closes the one
  dependency that move missed. It mints no CAP and changes no `SPEC.md`.
- **Governance.** `pixi.toml` is on the surface of `spec-pyforge-unifying-strategy`, `spec-pyforge-core`,
  `spec-pyforge-marshal`, `spec-pixi-candidate-currency`, `spec-deck-family-currency`, `spec-deck-family-lockstep`
  and `spec-pyforge-pages`; `scripts/deck_export.py` is on `spec-design-code-bridge`'s and `spec-modernist-identity`'s;
  the deck how-to and the pixi-tasks page are on `spec-pyforge-doctor`'s. Each Spec `spec-surface-check` names is
  reconciled on its memlog and stamped scoped.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag. It restores the behaviour Story 63.6
  promised, and a flag would keep the gap reachable.
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, 2026-10-14 (marp in the Guild env).

## Acceptance Criteria

- **AC1 — `marp` resolves in the Guild env.**
  - `[feature.pyforge-guild.dependencies]` declares `marp-cli = ">=4.2.3"`, the same floor as
    `[feature.local-recipes.dependencies]`, with a comment naming this story and the nodejs-26 note.
  - `pixi.lock` carries `marp-cli` 4.2.3 in `pyforge-guild`, `default`, `pyforge-foundry-full` and
    `pyforge-foundry-full-stack` on every platform each solves.
  - `pixi run --frozen -e pyforge-guild marp --version` exits 0 from a shell whose `PATH` carries no
    `.pixi/envs/local-recipes/bin`.
- **AC2 — `deck-export` runs from the session default.**
  - `pixi run --frozen -e pyforge-guild deck-export pyforge-scribe` exits 0 with no `PATH` prefix and regenerates the
    deck's three export artifacts (the PPTX pair needs Chrome on the host; without it the targets are skipped, not
    crashed — Story 23.3). The regenerated PPTX and stamps are restored afterwards, never committed.
- **AC3 — Every usage line names the Guild env.**
  - The `deck-export`, `deck-facts` and `deck-trio` descriptions read `Usage: pixi run -e pyforge-guild …`.
  - `scripts/deck_export.py`'s docstring and `run_marp`'s hint name `pixi run -e pyforge-guild deck-export`.
  - `docs/how-to/presentation-deck.md`'s Pixi note and § Generation name `pyforge-guild`; no line in the file sends
    a Guild task to `-e local-recipes`.
- **AC4 — The fix is pinned.**
  - `src/shared/packages/pyforge-steward/tests/meta/test_marp_in_guild_env_story_63_8.py` passes, and:
    removing the Guild feature's `marp-cli` line fails its first two tests; restoring `Usage: pixi run -e
    local-recipes deck-export` fails its third (mutation, each reverted).
  - `tests/scripts/test_deck_export.py::test_run_marp_hint_names_the_guild_env` passes, and restoring the
    `local-recipes` hint fails it (mutation, reverted).
- **AC5 — The derived files are regenerated in the same change.**
  - `environment.yaml` is re-exported (`pixi project export conda-environment -e build`) and byte-identical.
  - `pixi run --frozen -e pyforge-guild docs-environments -- --check` and `docs-pixi-tasks -- --check` exit 0.
  - `python scripts/pixi_env_matrix.py --check --dream docs/dreams/pyforge-unifying-strategy.md` exits 0.
  - `pixi run --frozen -e pyforge-guild llms-full-check` exits 0.
- **AC6 — Nothing else moves.** The `local-recipes` `marp-cli` line, every other Guild-feature dependency, the task
  names and commands, the deck pipeline's shell-out and `scripts/deck_export.py`'s behaviour with `marp` present are
  unchanged; `pixi.lock` changes only where `marp-cli` and its nodejs-24 build require.
- **AC7 — Green, and reconciled.**
  - `pixi run --frozen -e pyforge-steward pyforge-steward-test` exits 0, and so do
    `pixi run --frozen -e pyforge-guild pyforge-station-tests` (a `pixi.toml` change fires every station suite) and
    `pixi run --frozen -e pyforge-guild lint-types`.
  - Every Spec `spec-surface-check` names gets a surface-reconcile memlog entry naming the changed paths and this
    story, and is stamped scoped; `spec-surface-check` exits 0.

## Boundaries & Constraints

**Always:**
- Edit `pixi.toml` by hand and regenerate `pixi.lock` with `pixi lock`; never `pixi add` or `pixi update`.
- Keep the `local-recipes` `marp-cli` floor and its nodejs-26 note; move both sites together when they move.
- Restore every artifact `deck-export` regenerates during verification (`git checkout -- presentations/<slug>`).
- Reconcile every governed path on the memlog of each Spec that governs it, then stamp those Specs scoped
  (AGENTS.md pre-PR item 5).

**Never:**
- Never put a `local-recipes` path on a Guild task's `PATH`, and never move a Guild task back to
  `[feature.local-recipes.tasks]`.
- Never bump `marp-cli` past the conda-forge floor in this story.
- Never commit regenerated PPTX or `.stamp.json` files.
- Never edit herald's story specs or Spec companions for their historical `-e local-recipes` citations.

**Residual risk:**
- The Guild env on `win-64` and `osx-arm64` now resolves nodejs 24 instead of 26, as `linux-64` already did. Every
  node-backed tool the Guild carries (pptxgenjs-plus, codegraph, caveman-installer, bmad-module-skill-forge) ships
  a nodejs-24 build, and `[feature.python.dependencies]`' nodejs pin allows the 24.x line.
- `pyforge-foundry-full` grows by one package per platform; its union solve already held nodejs 24.

## I/O & Edge-Case Matrix

| Situation | Today (`846d8383f5`) | After |
|---|---|---|
| `pixi run -e pyforge-guild deck-export <slug>` | exit 1, `'marp' not on PATH — run via: pixi run -e local-recipes deck-export ...` | exit 0, three artifacts regenerated |
| following the hint (`pixi run -e local-recipes deck-export <slug>`) | refused by the session hook | the hint names `-e pyforge-guild`; nothing to refuse |
| herald `deck pull` / `deck sync-all` export step | fails at the first `marp` call | runs |
| the 2026-10-14 sweep's `PATH=".pixi/envs/local-recipes/bin:$PATH"` prefix | required | unnecessary; the pinned `bin/marp` wins |
| `deck-export` with no Chrome on the host | n/a (never reached `marp`) | HTML written, PPTX targets skipped (Story 23.3) |
| a future `guild-tasks` task that runs `marp` | nothing checks it | the meta test asserts the Guild feature carries `marp-cli` |
| a description written as `Usage: pixi run -e local-recipes <guild task>` | nothing checks it | the meta test fails, naming the task |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-5 (`pyforge-guild` is the default for every agent; Story 63.1),
  with CAP-152 (Story 63.6) for the task's move. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-14 (marp in the Guild env) entry.
- Epic: Epic 63 (`done` before this mint). A fix-forward story goes under the epic it belongs to, never a new epic
  (operator rule 2026-10-04); doctor Story 41.5's `epic_reopened_by_new_story` rule lets `epic-63` leave `done` with
  this key, as Story 63.7 did.
- Ledger key: `63-8-marp-resolves-in-the-guild-env-so-deck-export-runs-where-every-agent-runs`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Spec: the `spec-pyforge-steward` memlog records the evidence, the design and this mint.
- Surface: `marshal-policy.toml` `[epic_surfaces]."63"`, widened with this mint to the deck-export script and test,
  the deck how-to, the two regenerated pixi pages, `docs/map.yaml` and the unifying-strategy Dream's env matrix.
- Minted 2026-10-14 in one chain commit, with the code.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0. This is the station's
  `verify_commands` (MRS-GATE-010 binding), and it runs the new meta test.

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild marp --version` — expected: exit 0, `@marp-team/marp-cli v4.2.3` (AC1).
- `pixi run --frozen -e pyforge-guild deck-export pyforge-scribe; echo $?; git checkout -- presentations/pyforge-scribe`
  — expected: exit 0, `regenerated 3 artifact(s)` (AC2), tree restored.
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/meta/test_marp_in_guild_env_story_63_8.py -q`
  — expected: exit 0, 3 passed (AC4).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_deck_export.py -q` — expected: exit 0 (AC4).
- The AC4 mutations, one at a time, re-running the named test each time — expected: each fails the named test.
  Revert each and confirm with `cmp`.
- `grep -n "local-recipes" scripts/deck_export.py docs/how-to/presentation-deck.md` — expected: no usage line for a
  Guild task (AC3).
- `pixi run --frozen -e pyforge-guild docs-environments -- --check; pixi run --frozen -e pyforge-guild docs-pixi-tasks -- --check`
  — expected: exit 0 each (AC5).
- `pixi run --frozen -e pyforge-guild python scripts/pixi_env_matrix.py --check --dream docs/dreams/pyforge-unifying-strategy.md`
  — expected: exit 0 (AC5).
- `pixi project export conda-environment -e build | cmp - environment.yaml` — expected: exit 0 (AC5).
- `pixi run --frozen -e pyforge-guild llms-full-check` — expected: exit 0 (AC5).
- `pixi run --frozen -e pyforge-guild pyforge-station-tests` and `pixi run --frozen -e pyforge-guild lint-types`
  — expected: exit 0 each (AC7).
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and the scoped
  stamps (AC7).
- `pixi run --as-is -e pyforge-guild detectors-ci` — expected: no new finding against `main`.

## Review Triage Log

### 2026-10-14 — Review pass (hand-landed; reviewer separate from the implementing agent)

Diff read against this spec and Story 63.1's. Findings: none blocking. Checked: `marp-cli = ">=4.2.3"` sits in
`[feature.pyforge-guild.dependencies]` with the local-recipes floor and its nodejs-26 note; the lock adds marp-cli
4.2.3 to pyforge-guild, default and the two foundry envs and moves win-64 / osx-arm64 nodejs to the 24 line the
conda-forge builds need (linux-64 otherwise unchanged); the three Guild task usage lines, `scripts/deck_export.py`'s
docstring and hint, and the how-to say `-e pyforge-guild`; `marp --version` and `deck-export pyforge-scribe` exit 0
from the Guild env with no PATH prefix; the new meta-test fails under each of three reverted mutations and passes
here; `environment.yaml` re-exports byte-identical. Verdict: accepted; status moved to done at landing, ledger row
promoted by `dispatch_land_finalize`.

## Spec Change Log

- 2026-10-14: minted from the station Dream's 2026-10-14 (marp in the Guild env) entry. `type: fix`, no flag, no
  CAP. Bound to `spec-pyforge-steward` CAP-5 through Story 63.1, with CAP-152 (Story 63.6) for the task's move.
  Minted with the code in one chain commit; the evidence above is this change's own measurement.

- 2026-10-14 (landing): `docs/foundry/sbom-gaps.md` loses its `pin:marp-cli` row. The derivation (`scripts/sbom_gap_derive.py`) stops yielding the key once marp-cli is a Guild-feature pin composed into pyforge-foundry-full, and `tests/scripts/test_sbom_gap_derive.py::test_live_document_matches_derivation` redded the pre-push preflight on the stale row. Added to the surface; `sbom-gaps-check` exits 0 after.
