# Alignment inventory — verified findings (2026-08-22)

Two research passes (the 6.11 release surface during the upgrade; the v7
trajectory afterward) plus a local inventory. Every row was verified against
the live repo or upstream source — nothing assumed. CAP column = the
capability that closes it.

## Local misalignment

| # | Finding | Evidence | CAP |
|---|---|---|---|
| 1 | bmad-loop's three repo skills stale vs the 0.11 package | `bmad-loop-setup` 217 diff lines, `-resolve` 134, `-sweep` 7 vs `bmad_loop/data/skills/`; `init` refuses overwrite without `--force-skills` | CAP-2 |
| 2 | Seed template ships a retired name to every new station | `seed/templates/files/dream-first-workflow.md.j2`: "`bmad-loop` / `bmad-dev-auto`" | CAP-1 |
| 3 | 6 planning artifacts + AGENTS.md + 3 auto-memory entries name retired skills | epics.md of warden/steward/atlas/doctor/marshal, marshal PRD.md; 1 AGENTS.md ref; `feedback_skill_disambiguation` + 3 `bmad-dev-auto` memory entries | CAP-1 |
| 4 | 22 spec folders carry pre-6.11 memlog debt | 14 folders: `SPEC.md`, no `.memlog.md`; 8 folders: memlog without frontmatter — `memlog.py` refuses (hit live 4× during the upgrade landing). All 8 stations affected | CAP-3 |
| 5 | Living factory docs lost their reconciler | `bmad-document-project`/`generate-project-context` retired; `architecture-bmad-infra.md` is a 6.10-era description (re-grounded 2026-07-25, pin v8.81.0); 8 `project-context.md` rulebooks still consumed by build-auto persistent_facts (canary-proven) with no regenerator | CAP-7 |
| 6 | Marshal's policy layer blind to the 0.10/0.11 knobs | `policy.py`: zero hits for `review.on_timeout` / `on_status_contradiction` / `limits.dev_contract_nudge` / `[operator] enabled` / `[verify] stream_capture_kb` | CAP-4 |
| 7 | Marshal's status vocabulary predates 0.11 | `awaiting-operator` / `confirm` / `preserve_ref` / `sweeps_refused` unknown to `marshal status` + fleet-picture; DW-BL011-1 covers only the stall-check mislabel | CAP-5 |
| 8 | Hand-driven runs' deferrals need a human relay | 6.11 build-auto writes spec-frontmatter `deferred:`; bmad-loop bridges LOOP runs (`Engine._harvest_spec_deferrals`, 0.9.1+) but the 2026-08-22 canary's item needed manual relay to the tracked ledger (→ doctor DW-14-1-1); DW-BL011-2 filed | CAP-6 |

## Upstream v7 trajectory (all cited from bmad-code-org sources, 2026-08-22)

| Claim | Evidence | Confidence |
|---|---|---|
| 20 shims removed at the v7 cut — the only committed breakage | `v6-shims/README.md`: "Removal rides the v7 cut — never a 6.x minor"; installer prompt (#2746) counts 20; shims opt-out on fresh installs (#2728), `metadata.lifecycle: shim` | HIGH |
| v7 planning lane = `bmad-ticket` tree | `ticket-master` branch (active through 2026-08-19): `.bmad-obeya/` store, epic folders + `ticket.md`, `KEY-n-slug.md` stories, status the only stored fact, derived board/frontier; `bmad-create-epics-and-stories` → shim; `sprint-status.yaml` survives for in-flight v6 stories only | HIGH (branch-only) |
| `stories.yaml` being removed | PR #2672 body: "stories.yaml removed"; zero references in ticket-master's `bmad-spec/SKILL.md` (main has 6); V7-10 keeps the v6 epic-story path in build-auto | HIGH |
| config.yaml→TOML cutover at v7 | 6.11 notes: "the migration, not the cutover"; NOTHING on main moves it since v6.11.0 | MEDIUM — implied, unscheduled |
| No v7 date/milestone/migration doc | No milestones on either repo; npm `next` = 6.11.1-next.25 patch line; zero "v7" in docs llms-full.txt; richest source = ticket-master's V7-n commit trailers | HIGH |
| bmad-loop parallel fan-out not implemented | Issue #229 open, `needs-design` P4: every `scm.max_parallel` > 1 clamps to 1 | HIGH |
| Paige replacement / "explain this system" / bmad-ux+WDS | Announced in 6.11 notes; zero implementing PR/issue/branch | HIGH (absence) |
| Spec-template drift on main | #2761 removes "Ask First / Block If" from build/build-auto spec-template; #2737-#2739 replace checkpoint/scope menu codes | noted — recheck template-parsing tooling at next core bump |

## Wave-C decisions locked by this evidence

- `stories.yaml` / folder+id / `{spec-folder}/stories/`: **NOT adopted** (removed upstream).
- AGENTS.md managed block: **HOLD** (upstream ledger rework in flight: #2715/#2733/#2750/#2754).
- TEA: **no structural retrofit** (module not installed; 1.23.3 is a chore release).
