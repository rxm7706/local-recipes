---
chain: pyforge-herald
created: 2026-11-10
updated: 2026-11-10
status: final
type: audit
title: "Cutover readiness audit 2026-11-10: Herald"
companion: "docs/dreams/pyforge-unifying-strategy.md (Realization log, 2026-11-10 operator rulings)"
---

# Cutover readiness audit, 2026-11-10: Herald

One of nine read-only audits run at main `82a2b18828` for the A→B cutover (rebuild from Frame + Spec,
with A's code and tests as the oracle). The report below is the audit agent's own text, unedited except that a capability id of another project is qualified. Each
finding carries its own VERIFIED or INFERRED label; counts of test functions are static, and no suite
was run. The cross-cutting findings, the main session's spot-checks and the four operator rulings that
followed are in `_bmad-output/projects/pyforge-steward/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md`
§ *Cross-cutting findings* and on the Dream entry named above. Paths under `/tmp` in the report were
scratch and no longer exist.

---

HERALD A→B CUTOVER READINESS — read-only audit, 2026-11-10

Paths: R=/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes · H=R/src/shared/packages/pyforge-herald · S=R/_bmad-output/projects/pyforge-herald/planning-artifacts · SPEC=S/specs/spec-pyforge-herald/SPEC.md · DOS=R/docs-site/src/content/dossier/dossier.yml

VERDICT: Not ready as a rebuild input. The dossier's A→B state claims are still true today, but the Spec's status markers and superseded CAP text do not describe the code, B holds no herald oracle, and the dossier's dates, typed figures, herald section and CI tile are stale.

## MUST REFRESH (blocks cutover)

1. **Status markers are wrong, and the pre-measure was wrong.** Actual: 19 shipped, 37 ready, 5 in-progress (CAP-37/38/39/48/49), 0 retired. "retired=8" is the count of CAP tails containing the word (43,45,46,47,49,56,58,59). Ledger is 152/152 stories, 49/49 epics done, 152 story specs `done`, so 42 markers are stale. Genuinely unmet behind them:
   - CAP-36, CAP-50: live `sync-all` never reaches `unchanged` (DW-FU-23-6-1, medium, open).
   - CAP-38: no workflow calls the webhook; recording is the operator task `herald-ship-local`. Route in Spec `/api/herald/webhooks/on-ship`; code `/stations/herald/api/v1/webhooks/on-ship`.
   - CAP-39: scheduler is an optional local crontab line.
   - CAP-61: `/changes/` and `/status/runs/` publish "input absent" (DW-steward-43-6-1 open; no Guild step in pages.yml).
   - CAP-47, CAP-59: operator routine and snapshot refresh (DW-herald-egm-2026-11-01-1 open).
2. **Superseded CAP bodies still read as live.** CAP-44 success (`dashboard.yml` → `docs/dashboard/`), CAP-45 success (four retired tasks "exist"), CAP-46 success (CI annotation, `site-verify`), CAP-49 entire, CAP-52 intent and success (`docsite-check.yml`, `dashboard.yml`), CAP-53 (`docsite/build.py`, `pixi run -e site site-check`), CAP-56 success (a retired flag's OFF state). Retired code itself is gone (docsite/, both workflows, four tasks, `pages_second_host`).
3. **Spec has no Constraints, Non-goals or Assumptions section** (headings: Why, Capabilities, Fold provenance, Open Questions), yet line 96 and CAP-30 cite them.
4. **No herald oracle on B.** Case list has 40 `k-` rows (not 38), same ids on A and B, 0 herald rows. B has no `src/packages/pyforge-herald`. All nine Frames differ A vs B (B is pre-Epic-64 form).
5. **Capability ledger.** 61/61 ids match. All `rebuild`, including superseded CAP-45 and CAP-49. The 16 folded rows duplicate CAP-20..24, 26..28, 40..47, point at 12–15-line `status: absorbed` stubs with no capability text, and cover only 5 of 8 absorbed specs. 20 own rows carry the placeholder heading "from spec-…".
6. **Dossier CI tile.** `ci-status.json` `fetched_at` 2026-10-14 shows 3 stuck and 2 paused-manually, `review_by` 2026-11-01. Team memory records every surface resumed 2026-10-16/17. With the flag on in the dev overlay, the tile and `/status/ci/` publish that.
7. **Dossier herald section and § 09.** "47 / 12 stories / epics" (now 152/49); deck verbs listed 8 of 12 (missing publish, exports, sync-all, pptx-native); "MCP route not located" (now `django_herald_portal/mcp_asgi.py`: `start_notice`/`get_notice`, Epic 119); steward "15 duties" (skill says 31); `site/tools/verify_claims.py` is a dead path.
8. **Skill.** Compiled 2026-08-25 at 865b95dc95, 91 src commits behind. Documents 3 of 12 deck verbs; line refs off (L80→87, pyproject L63→74); CAP ids wrong. The fix is steward Story 29.5, `backlog`. `cli.py` help strings and about 110 src citations use pre-fold CAP numbers (pull "CAP-2", status "CAP-3").

## SHOULD RECHECK

- **Dossier A→B claims true today:** `cutover_root` default `local-recipes`; modes (923 rebuild, 93 A-only, 5 retire, no move, no `verified-in-foundry`); 44.3/44.7/44.12/44.13 done, 44.4–44.6 backlog, 44.10 plus seven blocked; Epics 53/54/60/64 done; SBOM locks on three platforms, full-stack linux-64, only libpq/postgresql 17.11; four case ids and `fcl:CAP-1`, `fnd:CAP-12` resolve.
- **Weak evidence behind true claims:** "B passes the slices" rests on a static expected column; B frozen 2026-09-14. "Adopt Frames: Done" holds on A only. "Wire the BMAD-suite" cites Epic 60, titled "Estate BMAD catalog".
- **Stale typed figures (typed → measured today):** fleet ~261K → ~282K; steward 35,770/74 → 41,500/80, tests 49,783 → 64,713; atlas 33,588/130 → 41,979/150; marshal 109,570/204 → 114,618/212; doctor 28,550 → 30,095; warden 20,194 → 20,562; herald 17,596/38 → 17,646/39; mason 9,424 → 9,481; scribe 5,893 → 5,973; core 4,049 → 4,299. Only 11 of 43 stats carry `check:`; the § 09.6 table and prose do not.
- **Re-verification:** `verify_claims.py --emit` at build (11 stats); `test_dossier_structure.py` checks § 10 sources resolve, not that they pass. Nothing checks A→B.3 against the steward ledger. Last dossier content commit fa6e11d4e4, 2026-10-15; no local build artifact exists.
- **Tests as oracle:** unit 69 files/1,372 fns, meta 28/229, integration 1/5. No `live_tree` split for herald (Story 117.4 covers steward and doctor only). 46 of 98 test files read the live tree (527 fns). Spec-named oracle tests run only in `pyforge-herald-test-built` (node + npm). Goldens frozen 2026-10-15 from the retired Jinja generator. 19 skip sites (node, pptxgenjs, env opt-ins, root), no xfail. Floor: unit 80, integration 70, touched modules, no exceptions.
- **Spec vs code:** CAP-11 says cost is "derived from sprint-status + bmad-loop journals"; `progress.py` has 0 such references. CAP-6 narration extractor is not in the package. Deck counts disagree: 7 (CAP-4), 9 (CAP-8/10, Genesis called a station), 10, 14, 17.
- **Code with no CAP:** MCP face `start_notice`/`get_notice`; `deck qa` and `scheduler run` verbs unnamed. Unmentioned modules over 300 LOC: `pptx_pipeline.py` 973, `pptx_native.py` 701, `deck_qa.py` 619, `agent_sdk_transport.py` 522, `herald-pages.ts` 675, `agent-surface.ts` 528. `scripts/deck_export.py` (326) is in no Spec surface. `marketplace.ts` (`spec-pyforge-steward:CAP-171`) sits in herald's surface.
- **Portability, would break on B:** `local_ship.py:31`; `verify_claims.py:91`; `deck_facts.py:281,302,520,616`; `web/package.json:8` (`../../../../..`); pixi.toml:3272 PYTHONPATH; shell-outs to root pixi tasks (`deck_pipeline.py:486,531`, `sync_all.py:342,384,416`). Legit: `presentations/`, `docs/dreams/`, `.herald/` under `--repo-root`.
- **Boundaries:** no sibling-station import; core only; `station_port` unused. No Django in base and no `dashboard/` dir. `station_api.py:32-33` imports `django_herald_portal` function-locally. Other stations reached as data only.
- **Chain:** PRD, spine, epics re-stamped 2026-11-05 (date only); no dangling FR arrow; 45 of 61 CAPs have none. Four memlog entries dated 2026-11-05 follow the 2026-11-01 re-derive. Deferred work: 68 open of 113 (1 high, 3 medium, 16 low, 48 unlabelled). The high row DW-21-7-1 (wasm poster) is open, though the tree copy now has 0 corrupt matches.
- **Frame:** four bullets covering deck seed/pull/status only; nothing on Pages or the dossier; "Lane 1 CMS stays steward" is what dossier § 09.4 calls wrong.

## NICE TO UPDATE

README "47 stories (12 epics)"; SPEC Why "1764 lines, 26 subparsers" (1,943 / 30); five companions untouched since 2026-08-02; `facts-ledger.md:50` and `deck_facts.py:81` say `-e local-recipes`; deck help "(seed/pull/status/watch)"; `export_notices_snapshot.py` unwired; `web/` built by no workflow; how-to has no pptx-native, exports, pptx-spec or watch. TODO/FIXME: 0. Vendored JS has origin and sha256 record.

## EVIDENCE

| Finding | path:line | V/I | How |
|---|---|---|---|
| Marker counts | SPEC:141-367 | V | script |
| Ledger all done | S/sprint-status-ledger.yaml | V | yaml count |
| Webhook route | H/src/pyforge/herald/webhook.py:181 vs SPEC:290 | V | grep |
| No Constraints section | SPEC:112,139,371,375 | V | grep |
| B has no herald | B origin/main ls-tree, case-list.md | V | git show |
| Ledger duplicates and stubs | R/docs/foundry/capability-ledger.yaml | V | script |
| Snapshot age | R/docs-site/src/content/ci-status.json | V file / I truth | json, memory |
| Dossier herald figures | DOS:518,526,545 | V | ledger, cli.py:229-468 |
| MCP face | R/src/shared/packages/django-herald/src/django_herald_portal/mcp_asgi.py:10-13 | V | read |
| Typed vs measured | DOS:1257-1340 | V | measurer run |
| Skill age | R/.claude/skills/pyforge-herald/0.1.0/pyforge-herald/metadata.json | V | git log |
| Story 29.5 backlog | R/_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml:185 | V | grep |
| No live_tree split | R/pixi.toml:3270 vs 641,3185 | V | grep |
| Cost not derived | H/src/pyforge/herald/progress.py | V | grep 0 |
| sync-all unproven | S/specs/spec-pyforge-herald/sync-proof-2026-09-19.md | V | read |
| Frames differ | R/docs/foundry/frames/stations/herald.frame.md | V | diff ×9 |

## NOT CHECKED

CI run 36277374647; live `gh` pause state; whether the claude.ai routine exists (no repo capture found); any suite, detector or site build. Intent-versus-code read closely for about 15 of 61 CAPs, the rest by script. Test path literals: 3 of 44 unresolved sampled, all fixtures or absence tests. Companions, django-herald code and Design-side state not reviewed. `scripts/deck_export.py` surface check covered `SPEC.md` files only.
