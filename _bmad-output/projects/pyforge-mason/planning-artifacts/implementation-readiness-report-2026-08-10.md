# Mason — Phase 1 backlog-truth audit (2026-08-10)

Gate report of `spec-artifact-chain-reconciliation` (CAP-2/CAP-4), second
station. Method: `audit-method.md`. Station suite at audit time: **350
passed** (`pixi run -e pyforge-mason pyforge-mason-test`, executed output —
re-run green after this landing's guard fix).

**The blind review overturned this report's first draft.** The draft read
"28/28 STILL-VALID, no correct-course gate — the cleanest chain audited so
far." The citation-verifier REFUTED that headline (while confirming the
factual spine, items 1–16 of its findings), and the blind-spot hunter
surfaced twelve findings including two cross-spec contradictions and a
promotion-gap recurrence of the warden-loss failure mode. The corrected
disposition stands below; the first draft's optimism is preserved only in
this paragraph, as the record of what the two-hunter pattern caught.

## Traceability matrix — the 28 remaining stories

| Claim | Ledger | Code reality (citation) | Verdict | Action |
|---|---|---|---|---|
| 2-1 the CFE port: adapter table + `CfeResult` + JSON extraction in `cfe.py` | backlog | `cfe.py:34-39` names this story as its extender, "None of that exists yet" — confirmed by scan (zero `CfeResult` outside the docstring, no adapter table, no `json` import). **But two of its six AC blocks are already satisfied**: "no import/importlib/exec of CFE code" is true today (no-op AC), and timeout kill+reap landed in `run_streamed` — only the *typed* timeout error remains (`errors.py` has 3 classes, no timeout type) | **STILL-VALID, narrowed** — remaining remit is smaller than the AC list | build as scoped; narrow at dispatch |
| 2-2 seam guard: `test_no_recipe_knowledge` + `test_adapter_sole_caller` | backlog | Neither file exists — but **the invariant the guard enforces is already breached by landed Epic-1 code**: `resolve.py:87` `_CFE_MARKER = Path(".claude/scripts/conda-forge-expert")` and `errors.py:104,115` hold CFE paths, while AD-3 (`ARCHITECTURE-SPINE.md:86-88`) says *only* `cfe.py` may — no carve-out exists for `resolve.py`/`errors.py`, though AD-5 *requires* resolution to live there. Building 2-2 as written fails on day one | **NEEDS-RESPEC** (reviewer overturned first-draft STILL-VALID) — a spec-vs-code contradiction: amend AD-3 with the carve-out or relocate the marker | `bmad-correct-course` before dispatch |
| 2-3 credential isolation | backlog | Zero `JFROG`/HTTP anywhere in the package (verified repo-wide); converges with the real CFE-side `_http.py:214-217` unconditional-injection finding | **STILL-VALID** | build as scoped; scanner must whitelist `__init__.py:17` importlib.metadata + `cfe.py:127,132` probe-script strings (recorded landmine) |
| 2-4..2-8, 2-10 recipe verbs (6 stories) | backlog | No literal CFE script paths in the epic text — **because the FR→script mapping was never made**: `ARCHITECTURE-SPINE.md:419-420` records **OQ-A1 open** ("a mechanical mapping the first story must produce"). These verdicts are *unfalsifiable, not verified* — nothing can rot because nothing binds. Surface partially inconsistent today: 4 non-private canonical scripts lack public wrappers (`feedstock_context/enrich/lookup, recipe_editor`), wrapper dir last touched v8.76 vs canonical v8.81 | **STILL-VALID (unfalsifiable pending OQ-A1)** ×6 — honest label, not the draft's earned-sounding one | OQ-A1 mapping is 2-1's first deliverable; verify the 4 wrapperless scripts then |
| 2-9 `mason recipe submit` | backlog | CFE's `submit_pr.py:128,147-149` accepts an **in-tree recipe slug only** (`_path_guard.py` confines to `<cfe-root>/recipes/`); PRD D-10 states this for `--to conda-forge` but never propagates it to FR-13/S-2.9, while S-2.4 promises recipes "written to the user-specified path" — **the two verbs compose into an unbuildable journey** (generate anywhere → submit only from the CFE checkout); `CFE_RECIPES_ROOT` exists but AD-13's closed knob set can't reach it | **NEEDS-RESPEC** — propagate D-10 or open the knob | `bmad-correct-course` |
| 3-1 engine protocol | backlog | `engines/__init__.py:11-14` names this story as extender; `probe_engine` seed only, protocol/registry absent as chartered | **STILL-VALID** | build as scoped |
| 3-2..3-9 package build + ship targets (8 stories) | backlog | `package.py:11` docstring-only seed naming **Epic 3** (epic-level, not story-level — draft overstated the anchor); `pyproject-build` gotcha pre-verified (`engines/__init__.py:16-20`); `models.py` convention hazard: spine `ARCHITECTURE-SPINE.md:270,313` requires `models.py` for `ShipReceipt`/`CfeResult`/`LockResult`, landed code puts every shape elsewhere, **no story owns creating it**, no meta-test guards it | **STILL-VALID ×8** with the models.py convention flagged | models.py ownership → same correct-course session |
| 4-1..4-4 environment lock/check (4 stories) | backlog | `environment.py:10` epic-level seed; `conda-lock >=4.0.2` present (`pixi.toml:1006`) | **STILL-VALID** ×4 | build as scoped |
| 5-1, 5-3, 5-4 seam-verification tests (3 stories) | backlog | Subjects are the not-yet-built 2-1/2-2 artifacts — correctly sequenced; 5-1's scanner inherits the 2-3 landmine | **STILL-VALID** ×3 | build after Epic 2 |
| 5-2 governance test | backlog | **Blocked by a live cross-spec contradiction**: AD-15 (`ARCHITECTURE-SPINE.md:210-217`) declares the CFE surface read-only *forever* and S-5.2 (`epics.md:1241-1242`) mechanizes zero-commits-to-it — while mason's own `spec-conda-forge-expert-rebuild` (draft, DEFERRED) declares those exact three paths its **rebuild target**, and its CAP-2 would *delete* the generator path Epic 2 binds to, gated on a `cfe.py` table that doesn't exist yet. `epics.md:1367` OQ-E5 (commit-range scoping) open. Epic 5 cannot certify while both are live | **CONTRADICTED** (the audit's first) | `bmad-correct-course`: reconcile AD-15 with the rebuild spec (or archive one) before Epic 5 dispatches |
| 5-5 Rule-2 CFE retrospective | backlog | Always-on repo rule; cannot stale | **STILL-VALID** | closeout story |

**Disposition: 24 STILL-VALID (6 of them unfalsifiable pending OQ-A1), 1
narrowed, 2 NEEDS-RESPEC (2-2, 2-9), 1 CONTRADICTED (5-2).** One
`bmad-correct-course` session covers all four gated rows plus the models.py
and AD-25/26 items below.

## Artifact findings

| # | Finding | Evidence | Action |
|---|---|---|---|
| AF-M1 | Ledger epic-1 rollup stale at `backlog`, stories 10/10 done | ledger + Tier-3; verifier confirmed key-by-key parity after fix | **Fixed**: Tier-3 → `done` (hand-edit sanctioned: no owning tool for epic keys), `sprint-ledger-sync` regenerated the tracked twin, board regenerated |
| AF-M2 | **6 of 10 done story specs untracked** (1-5..1-10 only in gitignored Tier-3) while `specs/README.md` asserted "no promotion gap" — the exact warden-loss failure mode, recurring | `git ls-files` vs `implementation-artifacts/`; `.gitignore:745` | **Fixed**: all 6 promoted to `planning-artifacts/specs/`, README claim corrected to name its own falseness |
| AF-M3 | AD-15 ("CFE surface read-only, forever") vs the mason-owned rebuild Spec declaring that surface its target; D-1 reopening recorded only in the rebuild spec's frontmatter | Hunter finding 1/2/10; OQ-E5 open | Cross-reference memlog entry appended to spec-pyforge-mason; reconciliation → `bmad-correct-course` (blocks Epic 5, see 5-2 row) |
| AF-M4 | `test-architecture.md` wholesale false: "4/38 done", "no cfe.py/package.py/engines", "119 tests", 3-unchecked-boxes for shipped 1.9 deliverables — **and one fabricated citation** ("derived from epics.md's own dependency table"; no such table exists, corroborated by spec-packaging-factory's own 0-of-30-parseable record) | `test-architecture.md:7,28,30-36,47,100,215-233` | Wholesale re-ground → `bmad-document-project` at mason re-plan (steward AF-6 class, worse: the fabrication is inside the document that exists to remediate fabricated content) |
| AF-M5 | AD-25/AD-26 have no owning story; three documents assert "all 16 ADs" while the spine carries 18 — and epics.md's `currency_review` *names AD-25/AD-26 as checked* while leaving the table at 16 | `ARCHITECTURE-SPINE.md:236,253`; `epics.md:32,60-79,183,792` | AD-ownership rows → same correct-course session |
| AF-M6 | `prd.md` `adopted_kernel:` pointed at nonexistent `projects/local-recipes/` path — the PRD's authoritative kernel unresolvable | `prd.md:9` | **Fixed**: repointed to the real spec-packaging-factory path |
| AF-M7 | Package README described a Story-1.1-only stub ten stories later (ships as the PyPI/conda distribution readme) | `README.md:9` | **Fixed**: Epic-1-complete prose |
| AF-M8 | Capability-tier guard had a second vacuity mode: a renamed/split guarded file is silently skipped (fixed tuple + skip-if-missing), unlike every rglob-based sibling guard | `test_capability_tiers.py:39,114-121` | **Fixed**: existence assertion added; suite re-run green (350) |
| OBS-1 | atlas 13-5's trending-candidates handoff has no mason-side intake story | `handoff.py:1`; zero refs in mason epics | Routed to the trendshift/decomposition chain (Phase 3) — not a mason defect |
| OBS-2 | mason's epics.md carries zero `**Status:**` lines — none of steward's false-status surface | grep = 0 | none; healthy contrast, recorded |

## Done-claim sample — 4 of 10 (Epic 1), all held

| Story | Key evidence |
|---|---|
| 1.2 CLI noun-verb structure | noun registration `cli.py:350,363`; `--format` placement `cli.py:297,335` |
| 1.5 CFE root resolution chain | `ResolvedCfeRoot`/`resolve_cfe_root` `resolve.py:65,92`; interpreter chain `resolve.py:135,154` |
| 1.7 degradation when CFE unavailable | probe + `ensure_*` guards `cfe.py:100-195`; capability-tier meta-guard on the seeds |
| 1.10 config/logging/child-output streaming | `run_streamed` `cfe.py:228`; live-stderr/timeout-kill/returncode/bare-str tests `test_cfe.py:266-403` |

Test inventory (corrected by review): **11 unit + 6 meta files**. Story 1.1's
evidence is the meta pair (`test_namespace_is_implicit.py`,
`test_no_config_file.py`), not a unit file — the draft's "dedicated unit file
per story" was wrong for exactly the one story it didn't sample.

## TEA / coverage-debt

No coverage-debt rows in Epic 1 (all ACs map to the green suite). Epics 2–5
unbuilt with test-stories chartered. One guard-quality fix landed (AF-M8).

## Verdict

Mason's backlog is **mostly dispatchable but not unconditionally**: 24 of 28
stand (6 honestly labeled unfalsifiable until OQ-A1's mapping exists), and
**four rows gate on one `bmad-correct-course` session** — 2-2's AD-3
carve-out, 2-9's D-10 propagation, 5-2's AD-15-vs-rebuild-spec contradiction,
plus models.py and AD-25/26 ownership. Dispatch order when re-spun: resolve
the correct-course items, then 2-1 → 2-2 before any verb story. The station's
code-side hygiene is genuinely excellent (zero TODO/FIXME, zero skips beyond
platform guards, self-documenting seeds); its prose artifacts
(test-architecture.md, READMEs, AD tables) had drifted exactly the way
steward's had — and its spec-promotion gap was the fleet's known worst
failure mode, caught live.
