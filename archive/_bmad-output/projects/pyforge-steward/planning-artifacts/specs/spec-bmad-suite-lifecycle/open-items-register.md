# Open-items register — every open BMAD-METHOD item in the fleet, partitioned

Companion of `spec-bmad-suite-lifecycle`. Surveyed 2026-09-06 at HEAD `35ddefbbc5` across the eight
sprint ledgers, epics files, Specs, deferred-work ledgers, memlogs, `customization-inventory.md`
and the session memories. Partition: **S** = a story in this PR's epics, **DW** = stays a
deferred-work ledger entry (robustness, not adoption), **W** = horizon watch, **X** = closed on
verification. Ids in the DW column are the ledger's own.

## Session 2 — the era tail (one branch, one `bmad-build` per story, in this order)

| # | Item | Partition |
|---|---|---|
| 1 | Steward ledger 14-6/14-7/14-8 read `backlog` though code is on main | X (fixed in this PR) |
| 2 | Story 30.1 — guard tuple +`bmad-checkpoint-preview` (21 ids), catalog-consistency test, glosses (`epics.md:4529,4552`, `architecture-bmad-infra.md:493`, `development-guide.md:716-717`); "orphan dir" premise corrected | S marshal 30.1 |
| 3 | Story 30.4 — bmad-loop skills meta-test (`importlib.util.find_spec`, not `importlib.metadata`) | S marshal 30.4 |
| 4 | Story 30.2 — retire 8 rulebooks; migrate `factory.py:216,950`, `bmad_drift_check.py:102,258`, `fleet_scan.py:1942,1966`, doctor fixture, SYNC-RUNBOOK; memlogs on `spec-bmad-drift-new-artifact-shape`, `spec-pyforge-doctor`, `spec-factory-console`; no `.sync-baseline.json` re-stamp | S marshal 30.2 |
| 5 | Story 30.3 — `architecture-bmad-infra.md` re-ground to 6.12.0 + glosses; snapshot header; CLAUDE.md:135 | S marshal 30.3 |
| 6 | CIS re-provision (C11, 15 lines / 10 files) | S steward 46.8 |
| 7 | skf catalog `pin: v2.1.0` | S steward 46.7 |
| 8 | Steward `--no-shims` | S steward 14.9 |
| 9 | Harness → `bmad-build-auto`, callers glossed, 8 homes re-rendered, guard widened | S marshal 30.5 |
| 10 | The `--no-shims` apply (first live CAP-6/7/8 exercise, same version) | S steward 14.9 (execution) |
| 11 | `@next` rehearsal (`6.12.1-next.0`; conflict path + pixi-bin fallback) | S steward 46.10 |

## Adoption and readiness (Epics 46/47 and the station relays)

| Item | Partition |
|---|---|
| Adoption register + posture amendments | S 46.1 |
| utility-skills provisioned; routing to herald/doctor/warden/scribe/marshal/steward | S 46.2, herald 18.2, doctor 20.4, warden 11.1, scribe 7.1, marshal 31.6 |
| TEA provisioned; `tea-test-review` task; generator retired; review lens; advisory | S 46.3, marshal 31.1–31.3, warden 11.2 |
| bmad-builder provisioned beside skf (cleanup-legacy guard tested) | S 46.4 |
| labs skill-by-skill (4) | S 46.5, atlas 24.1, herald 18.3 |
| manticore studio + first station mp4 | S 46.6, herald 18.1 |
| pipeline-truth installed-stage reads `_bmad/_config/manifest.yaml` (channel-product hole #1) | S 46.9 |
| eval-quality `__win` variant (hole #2) | S mason 14.1 |
| Doctor suite drift maps 7 of 13 (core-upgrade Q1; `DW-FU-14-1-2` kin) | S doctor 20.1 |
| render-HALT detector (G7) | S doctor 20.2 |
| `frozen-path-changed` detector (G11) | S doctor 20.3 |
| `spec-bmad-method-version-drift` status key + OQ write-back | X (this PR) + doctor 20.5 |
| eval-quality pilot (45.2 blocked → backlog) | S 45.2 |
| Readiness checklist + preflight-as-P7-signal | S 47.1 |
| `skf-export` root proof (G5) | S 47.2 |
| `_bmad/**` into Epic 44 surface; PROJECTS.md cutover layout (G1, G8) | S 47.3 |
| Foundry Stack `bmad-*` floor row (G9) | S 47.4 |
| Epic 44 dependencies on 14.9 / 30.x; 44.13 spine scope (G2, G3, G6) | S 47.5 |
| C5 spec-surface widening (P13) — plus the `sprint_plan.py` YAML writer wrapping `key: value` pairs past 80 columns (found 2026-09-06; the line-based promoter reads them as absent) | S marshal 31.4 |
| Loop-home readiness definition (G10) | S marshal 31.5 |
| Status flips: install-class-wiring, metapackage (+ Dreams); version-drift status key | X (this PR) |
| Dreams README rows (9); WDS line in `pixi-candidate-currency.md` | X (this PR) |
| Core-upgrade open questions Q2/Q3/Q4/Q5 | X (answered in memlog this PR); Q1 → doctor 20.1 |
| `customization-inventory.md` rows C3/C7/C10/C14/C15/C17 | X (refreshed this PR) |
| AGENTS.md pitfall line for the shim retirement | S (recorded by `bmad-project-context` after 30.5 lands) |
| `spec-bmad-method-core-upgrade` → `shipped` | W (a real future release through CAP-6..8) |

## Deferred-work entries that stay in their ledgers (robustness; not adoption)

Doctor `sources/bmad_method.py` family: `DW-FU-10-1` … `-10-1-7` (floor parsing: max-across-tables,
inline tables, compound ranges, abort-on-first-bad, missing evidence, `installation.version` vs
per-module `version`), `DW-FU-10-2` (shared Source dilutes grade), `DW-FU-10-3/-2/-3` (`check=True`
vs never-fail; live npm GET under `scope="repo"`; no integration test), `DW-FU-14-1` (largely closed
by 15.1, not retired), `DW-FU-14-1-2` (pin-floor-vs-installed — operator scope decision),
`DW-FU-15-1/-2` (`/tags` pagination; live-recipe test), `DW-FU-15-2/-2` (fresh-clone silence; named
meta-test), `DW-FU-11-3-3`.
Steward: `DW-FU-14-1` (naive CSV split), `DW-FU-14-5` (trap 8 automation), `DW-FU-15-1/-2`
(stubbed probes; loose wired census), `DW-FU-15-3/-2/-3/-4` (installer timeout; rollback;
`--list-modules` skip reasons; `_CIS_SKILL_NAMES` unasserted — **`-4` closes with 46.8**),
`DW-FU-15-4/-2` (network in prove-landed; `skip_native_spot_checks` flag), `DW-FU-6-2` (stale
`draft` note — retire), `DW-FU-42-2-11` (skf skill card duties).
Marshal: `DW-FU-25-4-2` (stale `bmad_loop 0.9.0` citations), `DW-FU-25-4-3`, `DW-FU-25-4-4`
(era-alignment `ready` while mid-flight — flips with Epic 30), `DW-FU-25-7` family (PROJECTS.md,
status totals, architecture sections), `DW-FU-7-5-8` (policy.toml class; `_bmad/skf/**` 7th
never-write pattern), `DW-FU-3-*` / `DW-FU-4-*` (bmad-loop state-contract hand-copies),
`DW-HYGIENE-2026-09-05-1` (`marshal sweep`). Mason: `DW-12-1-3`, `DW-12-3-1`, `DW-12-3-2`,
`DW-12-7-2`, `DW-5-5-2` (sync loop after the CFE MINOR bump). Atlas: `DW-FU-20-4-3` (CIS template
placeholder — re-check after 46.8), `DW-A1-6/7/8`.

## Watches

TOML cutover; `bmad-ticket` tree; v7 shim cut (mitigated — shims gone here); bmad-loop parallel
fan-out (#229); Paige / "explain this system"; `bmad-suite-metapackage/.memlog.md` has no
frontmatter (hand-append only); `spec-dream-to-code-model-self-verification` `tests/meta/` surface
entry is inert (no glob char) — governance fix, noted not done.

## Verified closed during the survey

16-recipe empty maintainers (`tests/meta/test_recipe_maintainers_nonempty.py`, v8.86.1); C3 pm-toml
text; C14 CLAUDE.md pointer (8906bfbb22); C15 AGENTS lines; C7/C17 `[modules.skf]` pins; C10
`module_version` 0.11.1; PR #1075's stale state (#1076 is HEAD); `bmad-generate-project-context`
"orphan" (not orphaned).
