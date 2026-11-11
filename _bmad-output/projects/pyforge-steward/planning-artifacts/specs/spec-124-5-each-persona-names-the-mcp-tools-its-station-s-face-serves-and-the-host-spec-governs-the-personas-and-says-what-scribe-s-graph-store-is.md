---
title: '124.5: Each persona names the MCP tools its station''s face serves, and the host Spec governs the personas and says what Scribe''s graph store is'
type: 'docs'
created: '2026-11-10'
status: 'backlog'
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
