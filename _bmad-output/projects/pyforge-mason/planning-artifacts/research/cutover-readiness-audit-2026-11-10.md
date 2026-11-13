---
chain: pyforge-mason
created: 2026-11-10
updated: 2026-11-10
status: final
type: audit
title: "Cutover readiness audit 2026-11-10: Mason and conda-forge-expert"
companion: "docs/dreams/pyforge-unifying-strategy.md (Realization log, 2026-11-10 operator rulings)"
---

# Cutover readiness audit, 2026-11-10: Mason and conda-forge-expert

One of nine read-only audits run at main `82a2b18828` for the A→B cutover (rebuild from Frame + Spec,
with A's code and tests as the oracle). The report below is the audit agent's own text, unedited except that a capability id of another project is qualified. Each
finding carries its own VERIFIED or INFERRED label; counts of test functions are static, and no suite
was run. The cross-cutting findings, the main session's spot-checks and the four operator rulings that
followed are in `_bmad-output/projects/pyforge-steward/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md`
§ *Cross-cutting findings* and on the Dream entry named above. Paths under `/tmp` in the report were
scratch and no longer exist.

---

## Mason + CFE cutover-readiness audit (read-only, nothing changed)

Root `R` = `/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes`. `SPEC` = `R/_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md`. `PKG` = `R/src/shared/packages/pyforge-mason/src/pyforge/mason`. `CFE` = `R/.claude/skills/conda-forge-expert`.

**Verdict:** The Mason CLI kernel (CAP-1..7) matches the code and has a mostly package-local oracle. The Spec as a whole is not rebuild-ready: CFE has no Spec, 10 "shipped" CAPs describe blocked or closed work, and the cutover seam code is unspecified.

### MUST REFRESH (blocks cutover)
1. **CFE has no Spec to rebuild from (fnd:CAP-3).** Coverage is CAP-18..26 (two lines each) plus CAP-32..34. The companion called "authoritative" is a 30-line absorbed stub. Unspecified surface: 76 scripts (46,978 LOC), 63 wrappers, 46 MCP tools, 130 gotchas, 145 test files (1,794 test functions), 0 tracked data files. The ledger has no CFE row of its own.
2. **CAP-14..17 marked shipped, ledger `rebuild`, but the campaign closed 2026-09-10 with both mirrors retired and briefs null.** The slice map is archived (v8.82.3, 68 scripts), not "under this Spec's directory". CAP-14..27 are each defined twice with different text. CAP-15 cites "(CAP-3)" from the old numbering. `scripts/dream_chain_check.py` does not exist.
3. **spec-pyforge-mason:CAP-8..13 (Presenton) marked shipped 2026-08-02, ledger `rebuild`.** The section itself says BLOCKED; none of the five named recipes exist.
4. **Factory-island code is absent from Spec, PRD, spine, epics and skills** (memlog only): `MASON_FOUNDRY_ROOT`, `MASON_FACTORY_ROOT`, `FactoryIslandMissingError`. The Spec says six knobs; the code has eight `MASON_*` vars. The error text advertises `--foundry-root`; no such flag exists.
5. **fnd:CAP-8 says the flip switches "Mason's targets".** Nothing in pyforge-mason, django-mason or CFE reads `pyforge.cutover_root`.
6. **Conda-forge ship is pinned to A's layout.** Ship requires `<cfe-root>/recipes/<name>/` exactly. The CFE submit script clones to `REPO_ROOT.parent/staged-recipes` and signs PRs "via local-recipes automation". Factory island is wired for `recipe build` only. No "never targets local-recipes" assertion exists (Story 44.9 blocked).
7. **Frame contradicts reality.** It says "Do not SKF-compile `.claude/skills/pyforge-mason/`" (last edit 2026-09-16); the skill was compiled 2026-10-05 under CAP-29. It does not mention `skills/stations/`, `package`, `environment` or `doctor`. B's ruling commit is unmerged (`DW-mason-egm-2026-11-1`).
8. **No working set or count ceiling on A** (44.8 blocked; fnd:CAP-5 A-only, expiry 44.8). `recipes/`: 7,886 dirs — 4,459 v1-only, 309 v0-only, 3,110 both, 8 neither.
9. **Code with no Mason CAP.** MCP tools `start_build`/`get_build`, `last_diagnose` and boot reconcile live in django-mason under steward's `spec-pyforge-unifying-strategy`. `boot.py`, `airgap_contract.py` and `engines/build_hooks.py` appear only in a "scope grew" note.

### SHOULD RECHECK
- **Status markers:** CAP-28..35 carry "Minted" only. CAP-32's grep clause fails today (`vc`, `ctng-compilers`; Stories 22.3/22.4 blocked).
- **Ledger:** id set equals the Spec's (CAP-1..35, no diff). 27 rows carry the placeholder heading "from spec-pyforge-mason". CAP-29 is the A-only row, expiry 44.5. CAP-31/32/35 are one-time `recipes/` campaigns in mode `rebuild` (INFERRED wrong).
- **CAP-2 "update shows the change before writing" is still false.** The verb help claims a plan in both paths; `--dry-run` help says the default writes.
- **Python floor:** pyproject `>=3.14`; package `pixi.toml` and the Spec constraint say `>=3.12`.
- **Status text:** Dream is `specified`; the Spec body says `realized` and `status: shipped`; frontmatter is `ready`.
- **Mason tests:** unit 24 files/1,056 functions, meta 16/291, integration 3/5 (3 slow, 1 clean skip, no xfail). No `live_tree` split. 7 modules (51 tests) read A's tree. `pyforge-mason-test` also runs a CFE meta-test. Real-CFE fidelity covers `validate` only; the other 9 scripts are stubs. Floor: 80% unit on touched modules.
- **CFE suite:** 107 unit, 34 meta, 4 integration files; 13 network marks, 31 skips, 1 xfail. 21 files read live `recipes/`. Runs `-e local-recipes test-ci`; PR lane `-e pyforge-guild test-ci-meta`.
- **CFE portability:** 44 of 76 scripts name `local-recipes` or `rxm7706`; 22 name a `recipes` path.
- **Mason `src` portability:** only A-shaped literals are `.claude/scripts/conda-forge-expert`, `recipes`, `build-locally.py` (would break on B without `MASON_CFE_ROOT`). No cross-station imports, no Django.
- **Skills:** the "six skills" statement holds. `mason-*` and `bmad-agent-mason` sit in no Spec surface. Station skill anchors are stale (`build_parser` L523→560, `main` L1080→1137).
- **django-mason:** declares only `django`; imports `pyforge.mason.boot` and `django_pyforge`; no tests.
- **Chain:** PRD and spine `2026-11-05` are re-stamps; last reviews 2026-09-14 and 2026-09-17, before CAP-28..35. All 57 FR arrows resolve; spec-pyforge-mason:CAP-8..28 have no FR; 0 of 16 NFRs carry an arrow.
- **Stories:** 126 done, 2 blocked (22.3 cycle in rattler-build render; 22.4 shared `track_features`), 1 backlog (33.2). Epics 22 and 33 in-progress. Story spec 5.4 says `blocked`; ledger says `done`.
- **Memlog:** 8 entries after the last re-derive (7 surface reconciles, 1 ruling retiring `reactpy-django`).
- **Deferred work:** 170 rows, 108 open (2 high, 12 medium, 22 low, 72 unrated). `DW-mason-25-*` open: 25-2-3 (high), 25-2-4, 25-4, 25-4-2, 25-4-3, 25-4-4, 25-7, 25-14-2, 25-15, 25-15-2, 25-16, 25-17, 25-18, 25-19, 25-19-4, 25-19-5, 25-22-2, 25-23. 25-2-3 ("92 remaining") is open beside CAP-35's marker (INFERRED stale).
- **SBOM:** 2 Mason rows (`feature:conda-smithy`, `feature:crm`), both `upstream`; todos `drafted` 2026-10-10, not filed.

### NICE TO UPDATE
- README is future tense ("verbs land in Epics 2-4").
- Spec numerics are stale (11 epics/50 stories, pixi 0.77.x, 67 scripts, 106 gotchas).
- 12 orphan `pyforge-mason/spec-*` entries in the spec-surface baseline.
- The unresolved-root message says "three" steps; the Spec says four.
- CFE version is consistent: SKILL, MANIFEST and CHANGELOG top are all 8.105.1 (Nov 5, 2026).

### Evidence
| Finding | path:line | V/I | How |
|---|---|---|---|
| CFE "Spec" is a stub | `R/archive/_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-packaging-factory/SPEC.md:1-30` | V | read |
| Campaign closed, mirrors retired | `…/spec-pyforge-mason/campaign-state.yaml:82,85,551,683` | V | read |
| Duplicate CAP-14..27 | `SPEC:88-153`, `688-740` | V | grep |
| Dead path | `SPEC:697` | V | `ls` |
| Presenton blocked but shipped | `SPEC:572,626-641` | V | read, `ls recipes/` |
| Factory island unspecified | `PKG/resolve.py:233-342`, `PKG/recipe.py:413` | V | grep of Spec and chain |
| Phantom `--foundry-root` | `PKG/resolve.py:315` | V | grep `cli.py` |
| No cutover flag reader | cutover `SPEC.md:123` | V | grep |
| Ship pinned to `recipes/` | `PKG/package.py:821`, `PKG/doctor.py:151` | V | read |
| Submit script A-shaped | `CFE/scripts/` submit script `:46-47,339` | V | python scan |
| Sole exit-3 path | `PKG/cli.py:1660-1669` | V | read |
| 10 wrapped scripts | `PKG/cfe.py:674-684` | V | existence check |
| Frame stale | `R/docs/foundry/frames/stations/mason.frame.md:18` | V | read, git log |
| Update writes without plan | `PKG/recipe.py:806-827`, `PKG/cli.py:805` | V | read, `--help` |
| Python floor split | `R/src/shared/packages/pyforge-mason/pixi.toml:22,39` | V | read |
| Anchor drift | `R/.claude/skills/pyforge-mason/active/pyforge-mason/provenance-map.json` | V | grep `def` |
| Sentinel recipes remain | `R/recipes/vc/recipe.yaml`, `R/recipes/ctng-compilers/recipe.yaml` | V | grep |
| MCP face outside Mason Spec | `R/src/shared/packages/django-mason/src/django_mason_portal/mcp_asgi.py:10-13` | V | baseline JSON |

### NOT CHECKED
- No tests, detectors or builds run. Test counts are static `def test_` counts, not collected ids.
- `recipe submit --help` skipped (session hook); read from source instead.
- B not inspected.
- Read in full: SPEC CAP text, `resolve.py` factory half, `exit_codes.py`. Sampled: `cfe.py`, `package.py`, `recipe.py`, `cli.py` by grep and excerpts.
- Feedstock-refresh companion, glossary, 131 story specs (frontmatter status only), Dream body: not read.
- CFE scripts' argv contracts versus Mason's adapters: not compared.
- Seeded per-module coverage floors: not located.
- The four hand-authored skills: grammar and G-ids grepped only.
