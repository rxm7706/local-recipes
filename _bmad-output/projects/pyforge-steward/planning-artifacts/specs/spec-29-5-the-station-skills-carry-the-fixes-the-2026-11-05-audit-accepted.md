---
title: "29.5: The station skills carry the fixes the 2026-11-05 audit accepted"
type: 'fix'
created: '2026-11-05'
status: 'done'
baseline_revision: '836a2ee286'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-4-the-station-skills-are-recompiled-to-cover-the-verbs-the-contract-names.md
deferred: []
declared_low_risk: false
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-121.2, S-122.4, S-124.5).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).
>
> **Unblocked 2026-11-13.** Every story its Deps name is `done` on branch `cutover-readiness-2026-11-10`. The operator's "Start build" consent covered the unblock; CLOSE-LEDGERS moved the key to `done`.

<intent-contract>

## Intent

**Problem:** The audit of 2026-11-05 accepted 20 findings against the compiled station skills. The skills lag the code: marshal's
says `--audit` reads whole files, steward's omits exit code 3, mason's hides its JSON contract and ship states, and warden's and
herald's give no exit codes. Two skills inherit their errors from source text, so a recompile alone reproduces them: herald's CAP
citations from `cli.py`, and scribe's staleness rule from `models.py` and `compile.py`.

**Approach:** Correct the source text first. Then put each fix in the `skill-brief.yaml` scope or the MANUAL region, and recompile
through `skf-update-skill`, as Story 29.4 did. Five deferred skill findings ride the same pass. STW-R-F2 and STW-R-F3 stay out,
because the `--yes` gate they describe is not in the parser until Story 118.3, which recompiles them.

Ledger key: `29-5-the-station-skills-carry-the-fixes-the-2026-11-05-audit-accepted`. Type / Effort / Deps: fix / L / S-121.2, S-122.4, S-124.5 (amended 2026-11-10 in place by the cutover-readiness mint; cross-station deps in the notes below).

### Living CAP citations

- **`spec-pyforge-unifying-strategy` CAP-15** — the station skills are SKF compiles of the station packages (canopy:FR-37).

## Acceptance Criteria

- **AC1 — Source first.** herald's `pull` and `status` help strings cite the right capability, and scribe's `models.py` and `compile.py` docstrings say `compiled_at`.
- **AC2 — The skills.** Each accepted and carried finding named in the Story's FR/AD line is fixed in its skill, and no `SKILL.md` is hand-edited outside a MANUAL region.
- **AC3 — The MCP runner.** Each skill says what its station's MCP runner does and does not run, as the code stands, whether or not the operator has ruled on `DW-steward-egm-2026-11-05-1`.
- **AC4 — The gates.** `pyforge-steward-test`, `pyforge-herald-test`, `pyforge-scribe-test`, `governance-currency` and the instruction-surface parity test exit 0 (commands, each expected exit 0: `pixi run --frozen -e pyforge-guild pyforge-station-tests`; `pixi run --frozen -e pyforge-guild governance-currency`; `pixi run --frozen -e pyforge-scribe env PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pytest src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py -q`), the `spec-pyforge-unifying-strategy` surface is stamped `--spec pyforge-steward/spec-pyforge-unifying-strategy`, and the owning Specs' memlogs name the recompiled paths. *(Amended 2026-11-10 in place: in the cutover-readiness PR no build story writes a Surface reconcile line or runs a stamp; closer Story 122.5 writes the host Spec's reconcile event and doctor Story 58.4 runs the scoped stamp.)*
- **AC5 — Steward's skill lists exit 3 and no retired verb (added 2026-11-10).** `grep -cE 'exit code 3|\b3\b.*(refus|could not run|not configured)' .claude/skills/pyforge-steward/active/pyforge-steward/SKILL.md` prints 1 or more, and `grep -c 'cutover plan/apply\|cutover apply' .claude/skills/pyforge-steward/active/pyforge-steward/SKILL.md` prints 0.
- **AC6 — Each skill points at its station's contract (added 2026-11-10).** `for s in atlas doctor herald marshal mason scribe steward warden; do grep -q 'contract.md' .claude/skills/pyforge-$s/active/pyforge-$s/SKILL.md || { echo $s; exit 1; }; done` exits 0, and each skill's MCP tool names, exit codes and flag keys are its station's `contract.md` rows.
- **AC7 — Every compiled file comes from a recompile, and the catalogs follow (added 2026-11-10).** Each `.claude/skills/pyforge-<s>/active/pyforge-<s>/metadata.json` carries a generation date on or after 2026-11-10 (`for s in atlas doctor herald marshal mason scribe steward warden; do python3 -c "import json,sys;m=json.load(open(sys.argv[1]));d=str(m.get('generation_date') or m.get('generated') or m.get('compiled_at') or '');sys.exit(not d>='2026-11-10')" .claude/skills/pyforge-$s/active/pyforge-$s/metadata.json || { echo $s; exit 1; }; done` exits 0; the key name is the one metadata.json uses); the SKF meta-tests exit 0 (`pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/meta/test_skf_steward_skill.py src/shared/packages/pyforge-steward/tests/meta/test_skf_domain_skills.py -q`, every `[SRC:]` reference resolving at HEAD); `pixi run --frozen -e pyforge-guild pyforge-station-tests` exits 0; `pixi run --frozen -e pyforge-guild bmad-estate-check` exits 0; `docs/reference/skills-catalog.md` is regenerated once with `docs-skills-catalog`.

## Boundaries & Constraints

- Parked at `backlog` by the session owner on 2026-11-05: a recompile pass is its own review.

**Never:**
- Never hand-edit a compiled `SKILL.md` outside a MANUAL region; never run `bmad-module-skill-forge uninstall`.

</intent-contract>

## Binding

Parent: `spec-pyforge-unifying-strategy` CAP-15

- Findings: the station research files `research/egm-audit-2026-11-05.md`.
- Epic: Epic 29.
- Surface: `marshal-policy.toml` `[epic_surfaces]."29"` covers neither `.claude/skills/pyforge-*/**` nor `docs/reference/skills-catalog.md` nor `docs/map.yaml`, the paths this story owns since its 2026-11-10 re-scope, so this story is hand-landed, not dispatched, as Story 29.4 was.

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite, the SKF meta-tests included).
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: exit 0.
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: exit 0.

**Story checks:**

- `pixi run -e pyforge-guild governance-currency` — expected: exit 0.

## Spec Change Log

- 2026-11-05: minted at `backlog` by marshal Story 113.18.
- 2026-11-10: amended in place by the cutover-readiness mint (steward-station unit): Surface (the herald, scribe and mason source-text corrections move to those stations' stories of the PR; this story keeps the briefs, the compiled skills, this spec and the skills catalog with its map stamp), Deps (same-station S-121.2, S-122.4, S-124.5; cross-station warden:S-25.3, warden:S-26.1, scribe:S-33.2, mason:S-37.3, mason:S-39.1, atlas:S-47.1, atlas:S-48.2, herald:S-50.3, herald:S-50.4, herald:S-52.2, doctor:S-56.3, doctor:S-57.2, marshal:S-114.2, marshal:S-114.3, marshal:S-115.3, marshal:S-115.4: the last story of each station that moves its source lines, because a recompile pins `[SRC:]` line references), Effort M -> L (compiled skills across eight stations), AC4's stamp clause and AC5..AC7. What each requester asked the recompile to carry: atlas its 13 MCP tools in context-snippet.md; doctor `flags kill-switch`, backlog-intake detail and the sources dispatcher; herald 12 deck verbs, ids from the folded Spec, contract.md and bridge-protocol.md in the brief's scope; marshal `run_challenge`'s new line, `--section` and `--dream-section`, the context verbs, nine marshal-mcp tools and the seed exit domain; mason the eight MASON_ variables, the factory-island build and that `recipe update` writes by default; scribe the staleness rule against compiled_at, `index build` with no --target, the plane plugin and nine exports in metadata.json; warden a compile from the current package; steward `cutover plan|flip` with no `apply` and exit code 3. STW-R-F2 and STW-R-F3 stay out until Story 118.3. The `[SKF Skills]` block of AGENTS.md is re-exported by scribe. Never run `bmad-module-skill-forge uninstall`.
