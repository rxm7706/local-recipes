---
chain: pyforge-scribe
created: 2026-11-10
updated: 2026-11-10
status: final
type: audit
title: "Cutover readiness audit 2026-11-10: Scribe"
companion: "docs/dreams/pyforge-unifying-strategy.md (Realization log, 2026-11-10 operator rulings)"
---

# Cutover readiness audit, 2026-11-10: Scribe

One of nine read-only audits run at main `82a2b18828` for the A→B cutover (rebuild from Frame + Spec,
with A's code and tests as the oracle). The report below is the audit agent's own text, unedited except that a capability id of another project is qualified. Each
finding carries its own VERIFIED or INFERRED label; counts of test functions are static, and no suite
was run. The cross-cutting findings, the main session's spot-checks and the four operator rulings that
followed are in `_bmad-output/projects/pyforge-steward/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md`
§ *Cross-cutting findings* and on the Dream entry named above. Paths under `/tmp` in the report were
scratch and no longer exist.

---

## Scribe A→B cutover audit (read-only; nothing run except CLI `--help`)

Root for all paths: `/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes/`. `SPEC` = `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md`. `PKG` = `src/shared/packages/pyforge-scribe`. V = verified, I = inferred.

**Verdict:** not ready as a rebuild seed. The Spec contradicts the code on the memory schema and CLI shape, 26 of 32 CAPs carry stale or missing status markers, the Frame has forked between A and B, and the seed itself is stated three ways. Instruction-surface paths and both catalogs hold up.

### MUST REFRESH (blocks cutover)
- **M1 Memory schema.** Spec says flat `name/description/type`; code and all 119 files use nested `metadata.type` plus optional `supersedes`.
- **M2 CAP-17 and CAP-18 are stubs** ("See absorbed memlog"). Their contract exists only in an archived 14-line memlog; the archived SPEC is an `absorbed` stub.
- **M3 Status markers.** All 23 `(ready)` CAPs (5–16, 19–26, 30–32) are realized by `done` stories, so the markers are stale. CAP-27, 28 and 29 have no marker, only "minted". The one open item is Story 29.2 (`backlog`, kill-switch retirement dated 2027-01-24), not a retro; retros are `optional`.
- **M4 CAP-4 says three top-level commands; the CLI has five** (`capture`, `recall`, `graph`, `index`, `catalog`). There is no `graph index`. These have no CAP:
  - `index move-list`, `index refresh` (`--declare`, `SCRIBE_COCOINDEX_EXTRA`), `capture --source`, `catalog --root/--output`
  - recall recency tie-break (Story 26.1) and the transcript cost ceiling (Story 3.3)
  - the nightly trigger installer and freshness check (Story 8.1)
  - MCP tools `start_recall` / `get_recall`
  - the Postgres DDL (four Liquibase changesets) and the DuckDB plane driver's env vars
- **M5 Supersession is unreachable from the CLI.** `capture()` takes `supersedes`, `scribe capture` has no flag, and 0 of 119 records use it. CAP-2 success and AD-4 cannot be exercised through the "sole public contract".
- **M6 Recall argv.** CAP-21 says the portal argv is binary, `scribe recall`, query. Code adds `--` and optional `--mode`; the memlog entry recording it (2026-11-06) postdates SPEC `updated: 2026-11-05`. CAP-22 says "always planning"; marshal also allows `memory`.
- **M7 Frame fork.** A's `scribe.frame.md` differs from B's in `type`, `identifier`, `name`, `inherits` and owner/maintainer, though AGENTS.md says Frames are B's. The body is four bullets and carries none of the 32 CAPs.
- **M8 Seed stated three ways.** A and B `AGENTS.md` say "Frame + Spec"; the cutover Spec says "Dreams plus memlogs only"; B says "do not rsync `_bmad-output`", where memlogs live. The steward ledger still holds 44-4 fold, 44-5 move and 44-6 at `backlog`, and 44-10 archive at `blocked`, against "never fold/move" and "A is never archived".
- **M9 Capability ledger.** The id set matches exactly (32 ↔ 32). The other 20 scribe rows point at `absorbed` stub SPECs with zero CAP text and empty `heading`; each duplicates CAP-5..16 or 19..26.

### SHOULD RECHECK
- **S1 Literals that break on B's tree:**
  - `catalog.py` paths to marshal source, `recipes/`, steward's adoption register and `.claude/skills`, plus the title "local-recipes"
  - graphify default target `src/shared/packages`, which is silently skipped when absent
  - test depth math `parents[5]` / `parents[6]`, and the meta-tests' root finder
  - Clean: no Django import and no cross-station import in scribe `src/`. Outside callers do import scribe internals (AD-7).
- **S2 Tests as oracle.**
  - Counts: unit 340 functions in 19 files, meta 57 in 5, no integration or conformance lane, plus 94 in `tests/scripts/` outside the package.
  - No Story 117.4 `live_tree` split for scribe (only steward and doctor have it); all meta tests and at least 3 unit modules read the live tree.
  - Without Postgres the tests FAIL (`pytest.fail`), never skip: `test_graph_store_pg` (15), `test_graph_store_operations` (pg half), `test_recall_semantic` (2).
  - Skips: 4 plane-driver tests never run in scribe's env; 7 "extra unavailable" tests skip wherever graphifyy or cocoindex is installed, which is `-e pyforge-scribe` itself. Also django importorskip, win32 ×3, git-missing ×2. No xfail.
  - Coverage floor: 80% unit, touched modules only.
- **S3 Recall stack.**
  - Default store is the gitignored per-checkout `graph.json`, so CAP-3's "identical from any worktree" holds only on the shared Postgres store.
  - The local `graph.json` is dated 2026-11-06 02:47, four days old.
  - Specced: the cluster on `127.0.0.1:5433` (CAP-31), the env split (CAP-28), graphify (CAP-6/7/9).
  - Not specced for B: schema DDL and `platform_app` grants, psycopg `<3.2.11` / libpq 17, the pgvector 0.8.1 cap with no win-64 build, the DuckDB plane, cocoindex, python-crontab / apscheduler / systemd unit, the git binary.
- **S4 Package metadata against the estate.** `pyproject.toml` extras ask `psycopg>=3.3.4` (estate caps `<3.2.11`), `graphifyy>=0.9.51` (0.9.89), `cocoindex>=1.0.20` (1.0.25). The package `pixi.toml` says python `>=3.12` against `requires-python >=3.14`.
- **S5 PRD.** 17 FRs with arrows only to CAP-1, 2, 3, 4, 27, 28 (none dangling); 26 CAPs have no FR. PRD, spine and epics dated 2026-11-05 are date re-stamps. `epics.md` has an unqualified `FR-45` and a missing input document.
- **S6 Memlog fidelity, 15 Spec folders.** Every one has a memlog, frontmatter, exactly one `updated:`, and memlog ≥ SPEC.
  - SPEC behind its memlog: herald 4, marshal 1, scribe 1, steward 8, cutover 4, regenerate-not-fold 1 (all `event`); capability-ledger 2 (one decision, one change).
  - `spec-pyforge-core` and `spec-pyforge-testing-charter` SPECs have no `updated:`; core has 29 events after its SPEC's last commit.
  - Doctor's `spec-19-1-…` folder has a memlog and no SPEC.md.
  - Story 44.13 is `done`. Its tool, `scripts/memlog_fidelity_check.py`, checks presence and a scratch diff, not `updated:` or SPEC-behind.
- **S7 Team memory.** `MEMORY.md` is 143 lines against the 200 cap; 119 links match 119 files. Superseded and never linked: 4 CI-pause entries (registry shows 0 paused), 18 of 19 session-close entries, 16 "landed in dispatch worktree" entries, the 2026-09-19 operator inbox, and "PR #1607 not merged".
- **S8 Stale citations in the Spec.** The Non-goal "Not CAP-14" cites line ranges that have all moved and `pg16` (CI is pg17). Eight `later-caps:CAP-n` cites resolve only in the archive.
- **S9 Spec `surface:` omissions.** `.claude/memory/**`, the estate catalog, `agent-instruction-notes.md`, `.vscode/settings.json` and `.claude/settings.json` are allowlisted, so ungoverned. `django-scribe`, the scribe skill and the changesets sit under steward's unifying-strategy Spec. `library-llms-full.md` sits under the marshal and steward Specs, not scribe's.

### NICE TO UPDATE
- **N1** AGENTS.md "1,926 recipes (57 as `/v`)": grep today gives 3,382 `meta.yaml` plus 7,143 `recipe.yaml`, 609 in `/v` form.
- **N2** README "all 9 stories shipped (2 epics)".
- **N3** SKILL.md: stale rule compares to `valid_from` (code uses `compiled_at`), the `index build` default, the missing plane plugin; `metadata.json` lists 5 exports against SKILL's 9.
- **N4** Unqualified ids: persona "FR-13 / FR-11" and "CAP-15"; `recall.py` comments use pre-fold CAP numbers.
- **N5** `pg16` comment in `pixi.toml`; "staged-recipes" in the package `pixi.toml`; ledger header says `-e local-recipes`.
- **N6** Derive artifacts: `## Constraints…` inlined into success bullets, truncated headings ("ingestrepo()").
- **N7** Catalogs look current. Estate catalog generated 2026-11-01; later source commits moved no derived fact. Library catalog already lists the 11-04 additions.
- **N8** Open deferred-work rows: 23 (2 medium, 12 low, 9 with no severity).

Held up: every path, anchor, task and env AGENTS.md names resolves; session denials 16 + 3 = 19; 31 steward duties; 10 `pyforge-*` and 9 `django-*` packages.

### Evidence
| id | path:line | V/I | how |
|---|---|---|---|
| M1 | SPEC:80,181; `PKG/src/pyforge/scribe/models.py:72-76`; `.claude/memory/README.md` § Schema | V | read; frontmatter script over 119 files |
| M2 | SPEC:126-131; `archive/_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-scribe-mines-raw-session-transcripts/` | V | read |
| M3 | SPEC:90-175; `sprint-status-ledger.yaml` (scribe); `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md` § 4 | V | script, 32 CAPs to stories |
| M4 | SPEC:88; `scribe --help` tree; `src/shared/packages/django-scribe/src/django_scribe_portal/mcp_asgi.py:11-13`; `src/platform/db/changelog/changes/pyforge-scribe-{1..4}*.sql` | V | help; grep counts in SPEC and glossary |
| M5 | `PKG/.../capture.py:61`; `cli.py` (0 hits) | V | grep |
| M6 | `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py:52-59`; `.memlog.md:279`; `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/planning_graph.py:97-123` | V | read |
| M7 | `docs/foundry/frames/stations/scribe.frame.md` vs B `origin/main` | V | diff |
| M8 | `AGENTS.md:10`; cutover `SPEC.md:201`; B `AGENTS.md`; steward ledger:235-249 | V | read (backlog = dispatchable is I) |
| M9 | `docs/foundry/capability-ledger.yaml` | V | yaml script |
| S1 | `catalog.py:60-84,679`; `extras/graphify.py:54-62`; `tests/unit/conftest.py:18`; `scripts/realization_register_lib.py:66` | V | grep |
| S2 | `PKG/tests/unit/conftest.py:79-92`; `pixi.toml:3225-3230` | V static, I on env effects | def counts, grep |
| S3 | `cli.py:364-365`; `compile.py:186-191`; `ls .claude/data/pyforge-scribe` | V; CAP-3 reading I | read |
| S4 | `PKG/pyproject.toml:10,23,26,32`; `PKG/pixi.toml:24,28` | V | read |
| S5 | scribe `prd.md:67-169`; `epics.md:377,385` | V | parse |
| S6 | 15 folders | V structure; I after-counts (first date in each entry) | script |
| S7 | `.claude/memory/MEMORY.md`; `docs/governance/ci-surfaces.yaml` | V counts; I "superseded" | script |
| S8 | SPEC:207 | V | sed |
| S9 | SPEC:25-53; `scripts/spec_surface_allowlist.txt:3,5,90` | V | grep |
| N1 | `AGENTS.md:445` | V | grep, single-line `url:` only |
| N7 | `docs/reference/bmad-estate-llms-full.md:13`; commits `bd154aaa17`, `bca2b3025b`, `6021fd673b` | I | git diff of derived facts |

### NOT CHECKED
- No suite, detector, `--check`, `memlog-fidelity-check`, `governance-currency` or Postgres run; all test behaviour is static reading.
- "main green since PR #1072", Claude Code 2.1.277 and B's PR #19 need network.
- CAP intent against code: every CAP's anchors resolved by script; behaviour read closely for CAP-1–4, 10–14, 21–22, 25–26, 32; the rest by grep.
- 57 story specs: filenames and ledger only.
- Memory staleness judged from index lines, not bodies.
- Spine, Dream (1,203 lines) and the other `.cursor` rules were grepped, not read.

Scratch scripts: `/tmp/claude-1000/-home-rxm7706--claude-spares-spare-nW1L3i/552e28f7-6060-4942-926f-c593d0973dbf/scratchpad/q1.py`, `/tmp/claude-1000/-home-rxm7706--claude-spares-spare-nW1L3i/552e28f7-6060-4942-926f-c593d0973dbf/scratchpad/q4.py`, `/tmp/claude-1000/-home-rxm7706--claude-spares-spare-nW1L3i/552e28f7-6060-4942-926f-c593d0973dbf/scratchpad/q5.py`.
