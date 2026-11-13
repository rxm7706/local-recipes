---
title: '124.5: Each persona names the MCP tools its station''s face serves, and the host Spec governs the personas and says what Scribe''s graph store is'
type: 'docs'
created: '2026-11-10'
status: 'done'
flag-exempt: docs-only
difficulty: medium
story: 124.5
spec: pyforge-unifying-strategy
surface:
  - .claude/skills/bmad-agent-atlas/SKILL.md
  - .claude/skills/bmad-agent-atlas/customize.toml
  - .claude/skills/bmad-agent-doctor/SKILL.md
  - .claude/skills/bmad-agent-doctor/customize.toml
  - .claude/skills/bmad-agent-herald/SKILL.md
  - .claude/skills/bmad-agent-herald/customize.toml
  - .claude/skills/bmad-agent-marshal/SKILL.md
  - .claude/skills/bmad-agent-marshal/customize.toml
  - .claude/skills/bmad-agent-mason/SKILL.md
  - .claude/skills/bmad-agent-mason/customize.toml
  - .claude/skills/bmad-agent-scribe/SKILL.md
  - .claude/skills/bmad-agent-scribe/customize.toml
  - .claude/skills/bmad-agent-steward/SKILL.md
  - .claude/skills/bmad-agent-steward/customize.toml
  - .claude/skills/bmad-agent-warden/SKILL.md
  - .claude/skills/bmad-agent-warden/customize.toml
  - docs/how-to/reach-a-station-mcp-endpoint.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md
context:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A stale instruction in fifteen persona files, persona files on no Spec surface, and two host-Spec corrections stations asked for; the host Spec is three memlog entries behind.

**Approach:** Edit only the tool lines of the personas. Re-derive `spec-pyforge-unifying-strategy` once through the anchored script render (both self-validate passes logged); the three amendments are already memlog `change` entries (mint, 2026-11-10), so this story renders them and writes no second copy. Claiming the persona files makes this story's own edits governed: its Surface reconcile line is closer 122.5's and the scoped stamp doctor 58.4's.

Ledger key: `124-5-each-persona-names-the-mcp-tools-its-station-s-face-serves-and-the-host-spec-governs-the-personas-and-says-what-scribe-s-graph-store-is`. Type / Effort / Deps: docs / M / S-122.2.

### Living CAP citations

- **`spec-pyforge-unifying-strategy` CAP-16** (personas; the surface gains the eight station persona directories), **CAP-20** (the closed table), **CAP-4** (the warden cross-cite) and **CAP-14** (the GraphStore drivers and schema): the three amendments were written to the memlog at mint; this story re-derives.

## Boundaries & Constraints

**Always:**
- Take every tool name from that station's contract.md (the dependency stories write them).
- Write the surface as eight lines, one per station persona directory.

**Never:**
- Never use the glob `.claude/skills/bmad-agent-*` (it would govern the installer-owned personas).
- Never qualify the template ids `FR-13`, `FR-11`, `CAP-15`, `CAP-16` in the personas (deferred row DW-steward-cutover-2026-11-10-10).
- Never point a persona at contract.md (the pointer goes in the skill, Story 29.5).
- Never touch a django-herald path.
- Never append a `Surface reconcile` line or run a stamp.

## Acceptance Criteria

- **AC1 — no persona names the fallback tool as the face.** Expected: exit 1 (no match).
  ```bash
  git grep -n 'station_face' -- '.claude/skills/bmad-agent-*'
  ```
- **AC2 — each persona names tools its station's contract lists.** Expected: exit 0, and every tool name written is a row of that station's contract.md MCP section.
  ```bash
  for s in atlas doctor herald marshal mason scribe steward warden; do grep -qE 'start_[a-z_]+' .claude/skills/bmad-agent-$s/customize.toml || { echo $s; exit 1; }; done
  ```
- **AC3 — warden's persona allows what shipped.** Expected: prints 0.
  ```bash
  grep -c 'No Wave B' .claude/skills/bmad-agent-warden/SKILL.md
  ```
- **AC4 — the pinned persona headings are unchanged.** Expected: prints 8.
  ```bash
  git grep -c '^## Allowed actions (CAP-16)' -- '.claude/skills/bmad-agent-*/SKILL.md' | wc -l
  ```
- **AC5 — every station's persona tests (the aggregate is re-run by Story 58.4).** Expected: exit 0 (until Story 124.2 lands, steward's package half runs without test_station_tests_trigger_map.py, which reds on other units' new reads by design; 124.2 restores the full `pyforge-steward-test`).
  ```bash
  for s in atlas doctor herald marshal mason scribe warden; do pixi run --frozen -e pyforge-$s pyforge-$s-test || exit 1; done && pixi run --frozen -e pyforge-steward env PYTHONPATH=src/shared/packages/pyforge-steward/src:scripts pytest src/shared/packages/pyforge-steward/tests/unit src/shared/packages/pyforge-steward/tests/meta -q -m "not slow and not live_tree" -n auto --dist loadgroup -p no:cacheprovider --ignore=src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_concurrency.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scope.py --ignore=src/shared/packages/pyforge-steward/tests/unit/test_preflight_scratch.py --cov=pyforge.steward --cov-branch --cov-report=json:.steward/coverage/steward-unit.json
  ```
- **AC6 — the eight station personas, and only they, are on the host surface.** Expected: prints 8, exit 0.
  ```bash
  grep -cE '^  - \.claude/skills/bmad-agent-(atlas|doctor|herald|marshal|mason|scribe|steward|warden)/\*\*' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md && test $(grep -c 'bmad-agent-\*' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md) -eq 0
  ```
- **AC7 — the how-to names real tools.** Expected: prints 0, or every remaining line says it is the fallback identity server.
  ```bash
  grep -c 'station_face' docs/how-to/reach-a-station-mcp-endpoint.md
  ```
- **AC8 — names resolve and citations hold.** Expected: exit 0.
  ```bash
  pixi run --frozen -e pyforge-guild governance-currency && pixi run --frozen -e pyforge-guild ad-citation-check
  ```
- **AC9 — herald's pinned sentence stays.** Expected: prints 1 or more for each file (1 and 2 today).
  ```bash
  grep -c 'Lane 1 CMS stays steward' .claude/skills/bmad-agent-herald/SKILL.md .claude/skills/bmad-agent-herald/customize.toml
  ```
- **AC10 — no django-herald path moves.** Expected: prints 0 (BASE is the `baseline_revision` in this story's spec frontmatter).
  ```bash
  git diff --name-only "$BASE"..HEAD -- src/shared/packages/django-herald | wc -l
  ```
- **AC11 — CAP-14 names the durable schema.** Expected: prints 1 or more (0 today).
  ```bash
  awk '/^- \*\*CAP-14 —/{f=1;print;next} f&&/^- \*\*CAP-/{f=0} f' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md | grep -c 'pyforge-scribe-4-graph-nodes-stale-column'
  ```
- **AC12 — the host Spec is not behind its memlog.** Expected: exit 0 with no known row naming spec-pyforge-unifying-strategy (the test is scribe Story 32.3's; if it has not landed, `git log -1 --format=%cs -- <SPEC.md>` is not older than the last dated entry of its .memlog.md).
  ```bash
  pixi run --frozen -e pyforge-scribe env PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pytest src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py -q
  ```

</intent-contract>

## Binding

Parent: `spec-pyforge-unifying-strategy` CAP-16, CAP-20, CAP-4, CAP-14

- Dream: `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth* (subsection *The steward Spec, suite and shared surfaces*) and `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the steward-station mint entry).
- Epic: Epic 124.
- Ledger key: `124-5-each-persona-names-the-mcp-tools-its-station-s-face-serves-and-the-host-spec-governs-the-personas-and-says-what-scribe-s-graph-store-is` (`backlog` at mint).
- Deps: S-122.2.
- Surface: `.claude/skills/bmad-agent-<station>/SKILL.md and customize.toml for atlas, doctor, herald, marshal, mason, scribe, steward and warden` (the tool lines only), `docs/how-to/reach-a-station-mcp-endpoint.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md` (re-derive only), `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md` (the three `change` entries were written at mint).
- Minted 2026-11-10 by the cutover-readiness mint (steward-station unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `git grep -n 'station_face' -- '.claude/skills/bmad-agent-*'` — expected: exit 1 (no match).
- `for s in atlas doctor herald marshal mason scribe steward warden; do grep -qE 'start_[a-z_]+' .claude/skills/bmad-agent-$s/customize.toml || { echo $s; exit 1; }; done` — expected: exit 0, and every tool name written is a row of that station's contract.md MCP section.

## Notes

- Cross-station deps (each writes that station's contract.md): warden:S-26.1, scribe:S-31.1, mason:S-38.1, atlas:S-47.1, herald:S-50.3, doctor:S-57.2, marshal:S-114.3; same-station: 122.2.
- Read on 2026-11-10 from django-*/mcp_asgi.py: doctor start_scan/get_scan, herald start_notice/get_notice, scribe start_recall/get_recall, marshal start_loop/get_loop with list_loop_story_tasks and marshal_watch, mason start_build/get_build, steward start_duty/get_duty, warden start_audit and its get tool, atlas start_run_pipeline/get_run and its pipeline tools.
- CAP-4 (operator ruling 2026-11-10 on warden): django-warden realizes spec-pyforge-warden:CAP-16, spec-pyforge-warden:CAP-17 and spec-pyforge-warden:CAP-29, the portal half split from spec-pyforge-warden:CAP-26 (A-only on steward:121.5).
- The 20 capabilities of the host Spec get no marker sweep here (DW-steward-cutover-2026-11-10-5, written by Story 122.5). The skill half of the finding (exit code 3) is Story 29.5.

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the first build attempt. Each finding, then what this round did.

1. **major. Where:** `.claude/skills/bmad-agent-atlas/SKILL.md` (the `mcp` line) and `.claude/skills/bmad-agent-atlas/customize.toml` (the MCP menu prompt), read against `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md` § MCP tools. **Problem:** AC2 and the Always rule ("take every tool name from that station's contract.md") fail for atlas. The persona names `start_run_pipeline` and `get_run`. django-atlas's `mcp_asgi.py` registers both on `POST /stations/atlas/mcp`, by wrapping `build_server()` in `django_pyforge.mcp_start_get.attach_start_get`. But atlas's contract.md lists only the thirteen package tools and has no `start_` row. AC2's first clause needs a `start_` name and its second needs every name to be a contract row, so for atlas both cannot hold. The tool names in the other seven personas are all contract rows. The first attempt reported the gap only in its run report, not in this spec. **Response:** the reviewer is right. The fault is in atlas's contract.md, not in the persona text (it matches the code) and not in the AC2 command. The reviewer gave no corrected command, and amending AC2's expectation for atlas would loosen what it checks, so this round leaves AC2 as written and does not change the persona text. The gap needs an integrator ruling, because contract.md belongs to atlas Story 47.1 and no atlas story still to build owns it. It is recorded under *Planned deferral (written at build)* below with its candidate owners.
2. **minor. Where:** AC12, `src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py`, which reads `src/shared/packages/pyforge-scribe/tests/meta/data/spec_behind_memlog_known.json`. **Problem:** AC12 exits 1. The render worked: the test no longer finds spec-pyforge-unifying-strategy behind its memlog. But seven known rows for that Spec are now stale, and the test's shrink rule fails on them. The same run also fails on 25 stale spec-pyforge-marshal known rows, and on spec-pyforge-steward being behind Story 122.2's 2026-11-11 event (fingerprint `6b8cc9e9dc14555e`). The first attempt recorded none of this here. **Response:** the reviewer is right. The known file is scribe Story 31.4's, and 31.4 depends on this story, so dropping the seven rows is a planned handoff. It is recorded under *Planned deferral (written at build)*. The spec-pyforge-steward gap is not this story's Spec: it goes to the steward closer, Story 122.5, which re-derives spec-pyforge-steward. The stale spec-pyforge-marshal rows sit in the same scribe-owned file and are outside this story. Both are reported in this round's run report.
3. **minor. Where:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md`, the Constraint that consumer paths `LOAD` DuckDB's `postgres` and `vss` extensions and never `INSTALL` them on boot. **Problem:** this story is the PR's one re-derive of the host Spec, and the SPEC.md it rewrites still cites an unqualified atlas decision id that steward's project does not define. AC8 passes only because that row is in `scripts/.ad-citation-baseline.json`. **Response:** fixed in this round (the reviewer's option a). A `(correction)` memlog entry qualifies the citation as `pyforge-atlas:AD-13`. Atlas's spine says its LOAD-only extension rule is that decision's discipline extended to extensions. A second anchored script renders the correction, and two self-validate passes are logged as memlog events. ad-citation-check now reports the baselined row as fixed and still exits 0. The same unqualified id in the Spec's companion `stack.md` is outside this story's files and is reported in the run report.

## Planned deferral (written at build)

- **AC12 waits on scribe's known-rows file.** Once this story's render is committed, spec-pyforge-unifying-strategy is no longer behind its memlog. That leaves seven known rows in `src/shared/packages/pyforge-scribe/tests/meta/data/spec_behind_memlog_known.json` stale, and the test's shrink rule fails on them: `9ebca7883397393b`, `6bc0466339ffb259`, `02c9ab63e2ede7a5`, `7c03a6a50f89d294`, `91721889365e8615`, `ec9eb3920501f4cf`, `9166ddac98a8c30f`. **Owner:** scribe:S-31.4, which owns that file, depends on this story, and drops the seven rows. AC12 passes only after that story.

## Review findings (build, round 2, 2026-11-11)

An independent reviewer failed the round-1 attempt. Each finding is listed below, followed by what this round did.

1. **major. Where:** AC2 for atlas: `.claude/skills/bmad-agent-atlas/SKILL.md` (the `mcp` line) and `.claude/skills/bmad-agent-atlas/customize.toml` (the MCP menu prompt), read against `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md` § MCP tools and § The HTTP face. **Problem:** round-1 finding 1 is still open. It was escalated, not fixed. The persona names `start_run_pipeline` and `get_run`, and this matches the code: `django_atlas_portal/mcp_asgi.py` wraps `build_server()` in `django_pyforge.mcp_start_get.attach_start_get`. But atlas's contract.md has no row for either name: the grep count is 0 for each, and the file is unchanged on this branch since atlas:S-47.1. So AC2's second clause fails for atlas, and the Always rule is broken. The Planned deferral gave the work to no story: atlas:S-48.4's files_owned does not include contract.md, atlas:S-47.1 is built, and no `## Integrator ruling` exists. **Response:** the reviewer is right on the facts. The reviewer's fix is an integrator ruling, not a change to this story's files. This story cannot close the gap inside its files_owned. contract.md is atlas's file. Dropping the two names would fail AC2's first clause. The reviewer does not say the AC2 command is wrong, so the oracle rule does not apply, and AC2 stays as written. As the reviewer asked, the persona text is unchanged: it matches the face. This round rewrites the Planned deferral to name the reviewer's preferred route as the proposed owner: atlas:S-48.4, with files_owned widened to contract.md § The HTTP face, adding the two rows and completing "serves the MCP tools above". The deferral also names the fallback, an AC2 amendment for atlas. The integrator is asked to write `## Integrator ruling` in this spec. Until then, AC2 is reported failing for atlas and only for atlas. The tool names in the other seven personas are contract rows, and they match each `django-*/mcp_asgi.py`.
2. **minor. Where:** the frontmatter and AC10 (`git diff --name-only "$BASE"..HEAD -- src/shared/packages/django-herald`). **Problem:** AC10 says BASE is the `baseline_revision` in the frontmatter, but the frontmatter has no such key, so the oracle is underspecified. It is not weakened. **Response:** the reviewer is right. The frontmatter is the mint's, and a build writes body sections only, so this round adds no key. The reading used here: BASE is `git merge-base origin/main HEAD` = `82a2b18828` (`82a2b18828fc834653907ba6c9f42f2ef15dbd35`), the branch's base. AC10 prints 0 with that BASE, and the working tree has no django-herald change either. The integrator or closer steward:S-122.5 should add `baseline_revision: 82a2b18828` to the frontmatter, or record this reading in an Integrator note.
3. **minor. Where:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md`, the `python-duckdb` row. **Problem:** the host Spec's companion still cites atlas's decision id with no qualifier. ad-citation-check passes only because the row is baselined. SPEC.md now cites pyforge-atlas:AD-13, so the Spec and its companion disagree. **Response:** the reviewer is right, and reports it as not attributed to this story. stack.md is not in this story's files_owned, and no story in the plan owns it, so this round does not edit it. No memlog line is written for it either: a `(correction)` entry with no render would put SPEC.md behind its memlog and fail AC12. The integrator should route it: either to steward closer S-122.5, or by widening this story to stack.md. The fix is one `(correction)` memlog line, then qualifying the citation as `pyforge-atlas:AD-13`.

## Integrator ruling (2026-11-12, before the chunk-5 retry)

This ruling binds the implementer and the reviewer. It answers the three open items of review rounds 1 to 3.

1. **Atlas's face tools (round 1 and 2, finding 1).** This story now owns `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md`, § The HTTP face only. Add a
   table there with two rows, in the shape the seven other stations' contracts use:
   - `start_run_pipeline` | `name`, `assertion` | starts a supervised run of one pipeline and returns `{"handle": …}`
     at once; the supervisor runs `run_pipeline` (`RUN_PIPELINE_TOOL`, a supervisor runner, not an MCP tool).
   - `get_run` | `handle`, `assertion` | reads the supervisor run the handle names.
   Say that both are registered by `django_pyforge.mcp_start_get.attach_start_get`, which
   `django_atlas_portal/mcp_asgi.py` wraps around `build_server()`, and complete the sentence "serves the MCP tools
   above" so it names these two as well. Leave § MCP tools as it is: it stays equal to `TOOL_SPECS`, and the atlas
   meta-test (`tests/meta/test_public_contract.py`) checks only that every derived name is present, so the new rows
   cannot red it. AC2 stays as written. The persona text stays as it is, because it matches the code. The proposed
   owner atlas:S-48.4 is dropped from the Planned deferral. 48.4's single memlog event names contract.md among the atlas
   paths this effort moved.
2. **AC10's BASE (round 2, finding 2).** BASE is `git merge-base origin/main HEAD`, which is `82a2b18828` on this
   branch. The round-2 reading is correct. No frontmatter key is added.
3. **The host Spec's `stack.md` citation (round 2, finding 3).** This goes to steward:S-122.5, the closer that
   re-derives spec-pyforge-unifying-strategy. 122.5 adds `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md` to its files. It writes one `(correction)` memlog
   entry qualifying the atlas decision as `pyforge-atlas:AD-13` and renders SPEC.md in the same pass, so the Spec is
   never behind its memlog. This story does not touch stack.md.

## Review findings (build, round 3, 2026-11-12)

Chunks 3 and 4 failed this story's review on one finding that no file of its own could close. The integrator's ruling above answers it and the two open minor items. What this round did:

1. **major (rounds 1 and 2, finding 1), closed by the ruling. Where:** AC2 and the Always rule for atlas, read against `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md`. **Problem:** the atlas persona names `start_run_pipeline` and `get_run`, which the face serves, but atlas's contract.md had no row for either. **Response:** under ruling item 1 this story owns that file, § The HTTP face only. This round added the two-row table there: `start_run_pipeline` (`name`, `assertion`) starts a supervised run of one pipeline and returns `{"handle": …}` at once, the supervisor running `run_pipeline` (`RUN_PIPELINE_TOOL`, a supervisor runner, not an MCP tool); `get_run` (`handle`, `assertion`) reads the supervisor run the handle names. The section now says both are registered by `django_pyforge.mcp_start_get.attach_start_get`, which `django_atlas_portal/mcp_asgi.py` wraps around `build_server()`, and the "serves the MCP tools above" sentence names both. § MCP tools is unchanged and still equals `TOOL_SPECS`; `src/shared/packages/pyforge-atlas/tests/meta/test_public_contract.py` passes in `-e pyforge-atlas` (16 passed, exit 0). Every tool name in the eight personas is now a table row of its station's contract.md, so AC2's second clause holds for atlas as well. The persona text is unchanged. The atlas row is dropped from the Planned deferral, and this story writes no memlog line for contract.md: atlas:S-48.4's single memlog event names it.
2. **minor (round 2, finding 2), settled by ruling item 2.** AC10's BASE is `git merge-base origin/main HEAD`, which is `82a2b18828` (`82a2b18828fc834653907ba6c9f42f2ef15dbd35`) on this branch. AC10 prints 0 with it, and the working tree has no django-herald change. No frontmatter key is added.
3. **minor (round 2, finding 3), routed by ruling item 3.** The host Spec's `stack.md` citation went to steward:S-122.5, which adds `stack.md` to its files, writes one `(correction)` memlog entry qualifying the citation as `pyforge-atlas:AD-13` and renders SPEC.md in the same pass. This story did not touch `stack.md`.

AC12 stays red in its planned window: spec-pyforge-unifying-strategy is no longer behind its memlog, and the test fails only on the seven stale known rows in the Planned deferral, which scribe:S-31.4 drops. The same run also reports stale spec-pyforge-marshal known rows and spec-pyforge-steward behind Story 122.2's event (`6b8cc9e9dc14555e`); neither is this story's Spec.
