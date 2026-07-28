---
doc_type: sprint-change-proposal
project_name: local-recipes
date: 2026-07-25
via: bmad-correct-course
scope: moderate
status: implemented
source_pin: 'conda-forge-expert v8.79.1'
artifacts_modified:
  - planning-artifacts/PRD.md
  - planning-artifacts/epics.md
---

# Sprint Change Proposal — ownership decomposition + currency re-sync

## 1. Issue Summary

`PRD.md` and `epics.md` were the last two artifacts left behind by the 2026-07-25
SYNC-RUNBOOK reconciler run, which deliberately excluded them from its write scope.
Two distinct problems, one structural and one of currency:

**Structural.** The system grew a **fifth part** (`src/shared/packages/pyforge-packages`,
five hatchling distributions under one PEP 420 namespace) that neither document knew
about. More fundamentally, `local-recipes` was **the only BMAD project no station
owned** — which is the root cause of its drift. Every other project is pulled forward
by its owning station's retro loop; this one had nothing pulling it, so the
SYNC-RUNBOOK existed to substitute for the missing owner.

**Currency.** The docs were not uniformly stale but **internally inconsistent**, which
is worse — a partial 2026-07-06 re-grounding updated some spots and left others:

- `PRD.md` line 40 said *"42-tool MCP API"* while lines 37 and 150 already said 46.
- `F3.2` said *"42 `@mcp.tool()` registrations"* in a row whose **own acceptance
  column** asserted *"All 46 tools"*.
- `epics.md` Epic 10 was titled *"+ 42 Tools"* with a goal of *"all 42 tool
  registrations"* — and an acceptance line reading *"All 46 MCP tools callable"*.

A reader had no way to tell which number was live.

## 2. Impact Analysis

| Artifact | Impact |
|---|---|
| `PRD.md` | New § 0 (ownership), new § Part 5 (F5.1–F5.5), 12 count corrections, feature total 57 → 62 |
| `epics.md` | New Epic 15 (delegating), Wave 6 row, Epic 10 corrections, 14 → 15 epics / 232 → 239 stories |
| Five product projects | **None** — deliberately. Epic 15 cites them; it does not restate them. |
| `architecture.md` | **Not modified** — and correctly so: the one defect reported against it was **retracted**, see § 5. |
| Any `SPEC.md` | **Not modified** — `bmad-spec` is their single writer. |

## 3. Recommended Approach — Direct Adjustment (chosen)

Decompose rather than reassign. Handing all five parts to one Smith would violate the
Charter's § The Lexicon §4 (*each works one craft, not all*): a single owner's retro
loop would then be grounding four other stations' work.

| Part | Scope | Owning Dream | Station |
|---|---|---|---|
| 1 | conda-forge-expert skill | `packaging-factory` *(practice)* | Mason |
| 2 | cf_atlas pipeline | `pyforge-atlas` | Atlas |
| 3 | FastMCP tool surface | `agent-tool-surface` **(authored 2026-07-25)** | Marshal |
| 4 | BMAD infrastructure | `pyforge-marshal` · `pyforge-genesis` · `regenerable-factory` · `agent-portability` | Marshal |
| 5 | pyforge-packages | the five product Dreams | Warden · Atlas · Herald · Scribe · Doctor |

The **document set** is owned by **Marshal via `regenerable-factory`** — the only
reading under which a cross-station artifact has a legitimate single owner: Marshal
owns *the ability to rebuild the whole*, not the crafts that fill it.

**Part 3 was the one genuine gap.** The 46-tool FastMCP surface — 9 PRD features — had
**no Dream at all**, surviving as a single bullet inside `packaging-factory`.

## 4. Detailed Change Proposals (all applied)

### PRD.md — structural
- **NEW § 0 Ownership** — states the document is an *integration view*, carries the
  decomposition table, and binds two consequences (Part 5 delegates; Part 3 got its
  Dream).
- **NEW § Part 5** (F5.1–F5.5). F5.2 records the load-bearing subtlety: **no**
  distribution ships `src/pyforge/__init__.py`, and that *absence* is the mechanism —
  a regression is silent.
- **§ Part 3** gains its owning Dream plus two open facts: the factory runs **two**
  FastMCP servers, and **a fresh clone gets zero tools** (manual `~/.claude.json`
  registration, no `.mcp.json`).

### PRD.md — currency (all live-verified)
| Was | Now |
|---|---|
| 42-tool MCP API | **46** |
| Parts 1-4 / "the four parts" | **Parts 1-5 / five** |
| 9 envs, ~50 tasks | **15 envs / 17 features / 154 tasks** (106 in `local-recipes`) |
| Part 1 "~44 scripts" | **66 Tier-1 / 57 Tier-2** |
| F1.7 G1-G87 | **G1-G106** |
| F4.5 "64 real skills / 65 entries" | **89 real skills across 93 dirs**, BMAD **6.10.0** |
| §6 metric 42 / 42 | **46 / 46** |
| Total features 57 | **62** (54 in parts + 8 cross-cutting) |
| ~1,600 recipes | **~1,660** (1,664 dirs, churny) |

### epics.md
- **NEW Epic 15** — Part 5, **delegating and story-light** (7 stories covering only the
  integration contract). E15.S5–S7 point at the five product projects as authoritative.
  ~100 product stories were **not** copied in.
- **Epic 10** — title/goal 42 → 46; and its acceptance claim that *"Claude Code
  auto-discovers the server"* was **false** and is corrected.
- Wave summary gains **Wave 6**; frontmatter 14 → 15 epics, 232 → 239 stories.

## 5. Findings reported, NOT fixed (outside scope)

1. ~~**`architecture.md` says the `pyforge-atlas` MCP server has 11 tools. It has 12.**~~
   **RETRACTED the same day — this finding was WRONG, and `architecture.md`'s 11 is
   correct.** The claim came from `grep -c '@mcp.tool()'` returning 12. One of those
   12 is a **prose mention inside the module docstring** (`server.py` line 9:
   *"matching the legacy server's ``@mcp.tool()``"*); the real decorators are lines
   28–78, and exactly **11** functions carry them — `list_atlas_datasets`,
   `list_atlas_pipelines`, `query_vizro_ai`, `read_atlas_dataset`, and the seven
   `run_*_pipeline` tools.

   Recording it rather than deleting it, because the failure mode matters more than
   the number: this repo wrote down *"verify the detector, not just the artifact"*
   earlier the **same day**, after two detector bugs propagated their own wrong
   numbers into docs and baselines. Then a naive `grep -c` did it again — the bad
   count reached this proposal, the PRD's `edit_history`, the epics' `sync_lineage`,
   and a commit message before anyone re-derived it. **A count regex that does not
   assert what it matched is not evidence.**
2. ~~Three operator-brief numbers were wrong~~ — **also mostly retracted.** Only
   **pixi tasks 154** (brief said ~152) held. The other two were my error, in the same
   way as finding 1:
   - **Tier-2 wrappers are 57, not 60.** `ls` counted every *file* in
     `.claude/scripts/conda-forge-expert/`, which includes `README.md` and two `.sh`
     build helpers. 57 `.py` wrappers.
   - **Test files are 100, not 98.** `find -name 'test_*.py'` misses the two
     `conftest.py` files. (`architecture.md` also cites *188* test files — a
     different, equally correct scope: Part 5's product packages.)

## 6. Left alone deliberately

- **§ 7 architectural-gaps table** — its `G1-G6` is a *different* numbering for
  **system** gaps, distinct from the `G1-G106` recipe-authoring gotchas. Untouched by
  every prior sync; untouched here.
- **§ 9 Deferred Work** — no DW row is demonstrably shipped in this span.
- **All `SPEC.md` files** — `bmad-spec` is their single writer.
- **`architecture.md`** — already re-grounded, and **verified correct** on every
  count this run challenged it on (11 atlas tools · 57 Tier-2 wrappers · 100 Part-1
  test files · 188 Part-5 test files). See § 5.

## 7. Handoff

**Scope: Moderate.** No code change; no story rescoped; no epic removed. The five
product projects are unaffected. Follow-ups for the operator:

1. ~~Correct the 11 → 12 tool count in `architecture.md`.~~ **Void — no change
   needed; 11 was correct.**
2. Decide the **two-server** question now owned by `agent-tool-surface`: federate,
   merge, or stay split.
3. Close the **zero-tools-on-fresh-clone** gap — the sharpest contradiction of
   `regenerable-factory`'s own promise.
