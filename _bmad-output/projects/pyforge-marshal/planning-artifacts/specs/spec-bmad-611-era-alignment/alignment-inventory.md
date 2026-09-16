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

## 6.12.0 re-check (2026-09-05)

BMAD-METHOD 6.12.0 (CHANGELOG dated 2026-09-03; GitHub release 2026-09-04).
Evidence is the tagged tree, the CHANGELOG, and a diff of the installed 6.11
skills against `v6.12.0` — never the release page. The `_bmad/` install is
still 6.11.0 (the apply is steward Epic 14's). Rows continue the numbering
above; CAP column = the 6.12-round capability that closes it.

| # | Finding | Evidence | CAP |
|---|---|---|---|
| 9 | Shim roster still 20, one seat swapped: `bmad-checkpoint-preview` is a new shim forwarding to the new `bmad-walkthrough`; `bmad-generate-project-context` (a 6.11 shim) is neither a 6.12 `v6-shims` entry nor a `removals.txt` entry — ~~an update leaves its 6.11 directory orphaned~~ **Corrected 2026-09-06:** NOT orphaned — at 6.12 it ships as `lifecycle: shim` under `src/bmm-skills/plan/` (steward catalog `data/bmad_core_releases/6.12.0.yaml:22-24`); every `skill-manifest.csv` row uses the `_bmad/bmm/<category>/` notation, so the "missing directory" is notation, not an orphan. The apply deletes nothing; it retires with the other 20 shims via the `--no-shims` apply (spec-bmad-suite-lifecycle CAP-10). Guarded ids become 21 (20 `v6-shims` + this plan-tree shim) | `src/bmm-skills/v6-shims/` (14) + `src/core-skills/v6-shims/` (6) at `v6.12.0`; `removals.txt` at `v6.12.0`; `.claude/skills/` 6.11 shim census (20) | CAP-8 |
| 10 | Shims are opt-in on fresh installs (`--shims`); the guard tuple and two living docs (`architecture-bmad-infra.md:493`, `development-guide.md:717`) still carry `bmad-checkpoint-preview` bare | CHANGELOG § Breaking; grep | CAP-8 |
| 11 | `persistent_facts = []` — the `file:**/project-context.md` glob is gone; the 8 rulebooks lose their runtime consumer. D1 (2026-09-05 planning session): accept the default; the AGENTS.md `bmad:context` block is the surface | diff `bmad-build-auto/customize.toml` 6.11 → 6.12; consumers `pyforge-doctor/.../sources/factory.py:216,950`, `scripts/bmad_drift_check.py:102,258`, `scripts/fleet_scan.py:1966`, SYNC-RUNBOOK rows 7–9 / 45–49 / 83–85 | CAP-9 |
| 12 | The AGENTS.md HOLD is moot: the `bmad:context` block is live since 2026-09-04 (`bd37dfd607`); 6.12 `bmad-project-context` adds `adopt` and a retain/rewrite/relocate/delete ledger | `AGENTS.md:8-58`; diff `bmad-project-context/SKILL.md` | CAP-9 (decision) |
| 13 | `llms.txt` / `llms-full.txt` discontinued; `CLAUDE.md:56`'s live-source pointer is dead; the local copy (generated 2026-08-17) is the last snapshot | CHANGELOG § Breaking; `CLAUDE.md:55-58`; `.claude/docs/bmad-method-llms-full.txt` header | CAP-10 |
| 14 | bmad-loop 0.11.1 installed; repo `bmad-loop-setup/assets/module.yaml` still says `module_version: 0.11.0` (1 line); `-resolve` / `-sweep` identical | `diff -r bmad_loop/data/skills .claude/skills` | CAP-11 |

Verified no-ops — recorded so nobody re-checks them:

| Claim | Evidence |
|---|---|
| `{diff_output}` → `{diff_file}` needs nothing here | zero hits in `_bmad/custom/`; zero in bmad-loop; the only occurrences are the installed 6.11 skill files the update replaces |
| Spec-template drift needs no parser change | "Block If" tier removed, review-log shape changed, `followup_review_recommended` semantics changed — but `status` / `deferred` / "blocking condition" are unchanged and are the only keys repo readers consume (`marshal/core/status.py`, `supervisor/intent_gap_preserve.py`, `scripts/deferred_work_intake.py`); "Block If" appears in repo code only inside comments and a test docstring |
| CAP-3 holds | `bmad-spec/assets/spec-template.md` and `memlog.py` byte-identical 6.11 → 6.12 |
| CAP-4 holds | bmad-loop 0.11.1 adds no policy key (its git ≥ 2.34 floor is a `validate` check, `git.version`) |
| No CAP-5 gap yet | 0.11.1's hard `stop-request.json` mode and mode-exact `graceful_stop_pending` have no marshal reader (grep: 0 hits) — re-check when a marshal surface shows stop state |
| bmad-ticket not in 6.12 | no `ticket` / `obeya` path in the `v6.12.0` tree |
| TOML cutover not in 6.12 | installer still generates `_bmad/{bmm,core}/config.yaml` (no `config.yaml` in either source tree, 6.11 or 6.12 — it is installer-generated); no cutover language in CHANGELOG 6.12.0 |
