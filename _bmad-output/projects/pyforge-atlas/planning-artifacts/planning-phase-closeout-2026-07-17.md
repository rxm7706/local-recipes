# Tier-2 Planning Phase Closeout — pyforge-atlas — 2026-07-17

**Verdict: planning phase COMPLETE.** Readiness gate: **READY** (iteration 1,
zero blocking findings). The effort is handed off to Tier-3 execution
(bmad-loop + bmad-dev-auto per spec § 2.5 graduated autonomy).

Intake spec: `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` (v5.6,
`status: in-progress` since intake). Groundtruth: § 3.3 snapshot (`58a6dcc`)
re-verified valid at intake HEAD `4cf1b74`
(`intake-groundtruth-2026-07-17.md`).

## 1. Artifact set (all tracked, this directory)

| Stage | Artifact | State |
|---|---|---|
| 0 | `intake-groundtruth-2026-07-17.md` | done |
| 1b | `agents-and-skills.md` (persona/skill record) | done |
| 1a | `prds/prd-pyforge-atlas-2026-07-17/` — `prd.md` (status: final) + `addendum.md` + validation report + 2 reviewer artifacts | validated, 0 open findings (post-fix grade Good) |
| 2 | `architecture/architecture-pyforge-atlas-2026-07-17/` — `ARCHITECTURE-SPINE.md` (status: final, AD-1..AD-23) + 4 reviewer/reconcile artifacts | lint clean, 0 findings |
| 3 | `epics.md` — 9 epics, 32 frozen-ID stories (0.1, A1–A3, B1–B10, C1–C2, D1–D3, E1–E2, F1–F4, G1–G3, H1–H4), decisions D-1..D-15 | validated 32/32, 22/22 FRs |
| 4a | `implementation-readiness-report-2026-07-17.md` | **READY**, 7 non-blocking observations |
| 4b | `../implementation-artifacts/sprint-status.yaml` | generated + validated (Tier-3, gitignored — see § 2) |
| 5 | this document | — |

Mode distribution (binding, from epics.md): 6 ATTENDED (0.1, B4, C1, D3, F1,
G2) · 4 DEV-AUTO (A1, A2, D2, H2) · 11 LOOP-S (A3, B1, B2, B3, B5, B6, B7,
B8, B9, B10, F4) · 11 LOOP-E (C2, D1, E1, E2, F2, F3, G1, G3, H1, H3, H4).

## 2. Sprint feed (Tier-3 — local-only by design)

`sprint-status.yaml` lives in this project's `implementation-artifacts/`
(gitignored per the three-tier rule, `.gitignore:719`). The generating
container is ephemeral, so the feed is **regenerable, not archival**:

```
scripts/bmad-switch pyforge-atlas
# then invoke the bmad-sprint-planning skill (unattended; it re-parses
# planning-artifacts/epics.md, carries modes + verify gates, wave-ordered,
# and preserves existing statuses if the file already exists)
```

Feed shape as generated: 50 `development_status` keys (32 stories + 9 epics +
9 retrospectives), all `backlog`; parallel `story_meta` with per-story
`spec_id`/`epic`/`wave`/`mode`/`verify_gate`/`q_gate`/`depends_on` for
bmad-loop / bmad-dev-auto consumption; header assumptions A-1..A-5. First
runnable story: **0.1** (Epic 1 / Wave 0, ATTENDED, no dependencies).
Spec § 14 also mandates per-wave re-planning, so the feed is refreshed at
every wave start regardless.

## 3. Carries into execution (from the readiness gate + sprint planning)

1. **OBS-3 / B5→C1 follow-through**: B5's "Dagster-scheduled asset" AC clause
   is only fully demonstrable after C1 — carry a follow-through check into
   Wave-C planning (B5 in-wave verification stays fixture-scoped).
2. **OBS-6 / D-6 `[ASSUMPTION]`**: F4 as the 11th LOOP-S slot — reconcile
   against the technical research's drivability map (spec § 13.4 reference)
   at each wave's sprint planning; already noted in the feed header.
3. **CIS two-spine precondition**: `DESIGN.md`/`EXPERIENCE.md` (spec § 2.4)
   must exist before D2 opens (Wave-D precondition, owner recorded in the
   readiness report).
4. **Keystone budgets**: B1/B2/F1 unsplittable — AD-18 pre-flight
   `session_timeout_min`/token raises are binding.
5. **PRD §4.6 cosmetic**: FR-10 cites only F2; the epics FR map (F2+F4) is
   authority.
6. **Environment-deferred checks**: `bmad-drift-check`, `bmad-groundtruth`,
   `llms-full-check` did not run in the planning container (no pixi) — all
   three are Wave-0 preconditions (AD-18); run them in the first
   workstation session **before** any loop run, together with hooks approval
   and the worktree symlink bootstrap.
7. **`bmad-switch` supersession**: every § 2.5/§ 14 `bmad-switch
   local-recipes` literal is superseded by
   `bmad-switch pyforge-atlas` (PRD § 9.11 / AD-18 / D-4).

## 4. Next steps (execution phase)

Per spec § 14 + § 2.5: Wave-0 preconditions → story 0.1 (attended) → Wave A
(A1 nebi scaffold DEV-AUTO, A2 catalog DEV-AUTO, A3 first loop story +
worktree smoke) → Wave B loop-driven at per-story-spec-approval → waves C–H
per the mode map, PR per wave, legacy retirement only after B4 parity (Q1).
Rule-2 CFE retro at effort closeout is already tracked in the epics.

Independent, time-sensitive operator action (market-research carry, not a
story): the conda-forge Security SIG window (CRA clock 2026-09-11) — engage
with the atlas identity layer as seed infrastructure; no migration code
required.

## 5. Unattended planning-chain runbook (reusable)

This phase ran end-to-end unattended in a remote container (2026-07-17),
one orchestrator + one subagent per stage, commit+push between stages, no
human pauses. Recipe (any future Tier-2 intake):

1. **Scaffold**: create `_bmad-output/projects/<slug>/{planning,implementation}-artifacts`
   + `.bmad-config.toml` + PROJECTS.md row; `scripts/bmad-switch <slug>`
   (verify marker/symlink agreement); groundtruth note; spec `status:
   in-progress`; CLAUDE.md row move. Commit.
2. **PRD**: subagent invokes `bmad-prd` (create → validate → fix) with the
   spec + analysis artifacts as inputs. Unattended rules: no elicitation
   pauses; open questions at the spec's recommended defaults; every
   resolution recorded in a "Decisions & Assumptions (unattended intake)"
   section. Parallel lane: persona/skill record doc. Commit.
3. **Architecture**: subagent invokes `bmad-architecture` (PRD + spec target
   sections + technical research + brownfield docs). Commit.
4. **Epics**: subagent invokes `bmad-create-epics-and-stories` with frozen
   spec story IDs as a hard constraint. Commit.
5. **Parallel pair**: `bmad-check-implementation-readiness` (iterate to
   READY) ∥ `bmad-sprint-planning` (Tier-3 feed). Commit.
6. **Closeout**: this document's shape. Commit + push.

Operational notes: BMAD create-skills spawn their own reviewer subagents and
may yield mid-flow — re-wake them to collect reviews and apply fixes; keep
WIP snapshots committable at any instant (stop-hook-clean); the sprint feed
never gets tracked (Tier-3), its regeneration command gets recorded instead.

---

## Addendum — project slug rename (2026-07-17, post-merge)

Owner decision after PR #66 merged: project slug renamed
`conda-forge-atlas-datapipeline` → **`pyforge-atlas`** (aligns with the
sibling `pyforge-warden` naming family). Applied as a rename-in-place, NOT a
re-run: `git mv` of the project directory + both dated run folders
(`prds/prd-pyforge-atlas-2026-07-17`, `architecture/architecture-pyforge-atlas-2026-07-17`),
plus a global reference update across all planning artifacts, PROJECTS.md,
CLAUDE.md, the spec § 1 status line, and the Tier-3 files (story 0.1,
sprint-status.yaml). `scripts/bmad-switch pyforge-atlas` re-pointed marker +
symlinks; repo-wide grep confirms zero stale references.

**The readiness verdict (READY) carries over unchanged** — no artifact
content was altered beyond the slug string; FR/story/AD numbering untouched.
Every `bmad-switch conda-forge-atlas-datapipeline` instruction recorded in
the artifacts (PRD § 9.11 / AD-18 / epics D-4 / story 0.1) now reads
`bmad-switch pyforge-atlas`.

---

## Addendum — Wave 0 complete (2026-07-17, attended)

Story 0.1 signed off by the owner: `cf-atlas-legacy` forged via
**bmad-module-skill-forge@2.0.1** (SKF provisioned per owner decision;
install commit `b18cbb5`, artifact commit `6658049`). Evidence: SKF gates
100/100; 130-entry provenance map; independent fresh-agent battery PASS
(all citations line-exact, negative probe correct); meta-tests 1009/0;
drift-check green post-landing. Wave-0 preconditions ledger recorded in the
Tier-3 story file — sole open item: per-machine bmad-loop hooks approval on
the workstation. Epic 1 done; next runnable story: **A1** (nebi scaffold,
DEV-AUTO). Retro-ledger items for the Rule-2 closeout: D1 `_PARTITIONDATE`
spec-vs-code divergence; D3/D4 symbol-location corrections; the
fresh-container pixi `--frozen` + `build_artifacts` stub gotcha.
