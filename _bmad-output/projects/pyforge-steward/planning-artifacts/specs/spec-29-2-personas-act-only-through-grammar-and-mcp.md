---
title: Personas act only through grammar and MCP
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: ddafd7c6d88722e3d960aadd04239546d124b043
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md
  - .claude/skills/bmad-agent-dev/SKILL.md
  - .claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** An agent asked to do scribe work can freelance against the filesystem or call random HTTP. FR-38 / CAP-16 require each **03** station to be addressable as a persona that acts only through FR-13 grammar and FR-11 MCP.

**Approach:** Author one BMAD launcher/agent skill for the 29.1 proof station (`scribe`). It consults the CAP-15 `pyforge-scribe` content skill and may only emit grammar (`pyforge scribe …`) and MCP (`POST /stations/scribe/mcp`). Demonstrate one end-to-end station task as a checked transcript. Do not SKF-compile the persona.

## Acceptance Criteria

- Given the scribe persona, when it completes a station task, then the transcript contains only `consult_content_skill`, FR-13 grammar, and FR-11 MCP.
- Given a transcript that includes direct filesystem or ad-hoc HTTP, when the contract checker runs, then it fails.
- Given a persona skill that permits filesystem or ad-hoc HTTP, when the contract checker runs, then it fails.
- Given the persona package, when inspected, then it is a BMAD launcher (`SKILL.md` + `customize.toml`, `resolve_customization.py`) that consults `.claude/skills/pyforge-scribe/`, is not SKF-compiled, and does not replace `conda-forge-expert`.
- Given `src/platform/`, when this story's diff is scanned, then no `pyforge.*` import is added.

## Boundaries & Constraints

**Always:** Write specs under `_bmad-output/projects/pyforge-steward/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`. Proof station is scribe. Personas consult CAP-15; they are not compiled by SKF.

**Block If:** A change would SKF-compile the persona, replace `conda-forge-expert`, put `pyforge.*` under `src/platform/`, or start Story 29.3 / Epic 30.

**Never:** Five-tier CI check (29.3). Minting personas for 01/02 work. Compiling all eight personas. Hand-editing `CLAUDE.md` / `AGENTS.md`. Importing `pyforge.scribe` internals (package AD-7). Copying station duty logic into the persona skill.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Golden task | Scribe recall transcript (consult + `pyforge scribe recall` + MCP POST) | Checker accepts | No error expected |
| Freelance FS | Same transcript plus a filesystem event | Checker raises | Fail the test if accepted |
| Ad-hoc HTTP | Same transcript plus `GET https://example.com` | Checker raises | Fail the test if accepted |
| Permissive skill | Skill text that allows Read/Write or curl | Contract test fails | Fail if the live skill matches |
| Not SKF | Persona dir | No `metadata.json` `generated_by: create-skill`; has `customize.toml` | SKF layout fails the test |
| Host import | `git diff origin/main -- src/platform` | No new `import pyforge` | Any such import fails |

</intent-contract>

## Code Map

- `.claude/skills/bmad-agent-scribe/SKILL.md` — **new** BMAD launcher (activation + CAP-16 allow/forbid). Pattern: `.claude/skills/bmad-agent-dev/SKILL.md`
- `.claude/skills/bmad-agent-scribe/customize.toml` — **new** `[agent]` + menu of grammar/MCP prompts only (no `bmad-build`). `persistent_facts` must `file:` the CAP-15 skill
- `.claude/skills/bmad-agent-scribe/transcripts/scribe-recall-e2e.json` — **new** golden transcript for `scribe recall`
- `.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md` — CAP-15 consult target (read-only)
- `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py` — FR-13 grammar (read-only; `pyforge scribe …`)
- `src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py` — FR-11 `asgi_for_station` / `POST /stations/<name>/mcp` (read-only)
- `src/shared/packages/pyforge-steward/tests/meta/test_station_persona.py` — **new** FR-38 / canopy:AD-17 gates (I/O matrix)
- `.claude/skills/conda-forge-expert/` — must remain hand-authored (read-only)
- `src/platform/` — do not add `pyforge.*`

## Tasks & Acceptance

**Execution:**
- `.claude/skills/bmad-agent-scribe/SKILL.md` — author BMAD persona that consults CAP-15 — FR-38
- `.claude/skills/bmad-agent-scribe/customize.toml` — launcher config; grammar + MCP menu only
- `.claude/skills/bmad-agent-scribe/transcripts/scribe-recall-e2e.json` — one station task end to end
- `src/shared/packages/pyforge-steward/tests/meta/test_station_persona.py` — I/O matrix; fail on FS/HTTP freelance

**Acceptance Criteria:**
- Given a station persona, when it completes a station task, then the transcript shows only FR-13 grammar and FR-11 MCP — no direct filesystem and no ad-hoc HTTP.
- Given personas, when inspected, then they are BMAD launcher/agent skills that consult the CAP-15 content skill.

## Design Notes

Consult of CAP-15 is `kind: consult_content_skill` targeting the version-resolved `pyforge-scribe` `SKILL.md`. That is activation, not freelance IO. Freelance is any other filesystem kind, or HTTP that is not `POST` to `/stations/scribe/mcp`.

Grammar argv must start `pyforge`, `scribe` (unified dispatch). Do not invoke the `scribe` binary as a second public grammar.

Do not SKF-compile: no `provenance-map.json`, no `generated_by: create-skill`. 29.3 will later require a persona on every 03 station; this story proves one.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 0, low 2)
- defer: 0
- reject: 8
- addressed_findings:
  - `[low]` `[patch]` checker now rejects GET on the MCP path and `scribe` without `pyforge` as grammar
  - `[low]` `[patch]` checker now rejects CAP-15 consult of graph.json and MCP POST to another station

## Auto Run Result

Status: done

Summary: BMAD launcher `bmad-agent-scribe` consults the CAP-15 `pyforge-scribe` content skill and may only emit FR-13 `pyforge scribe …` and FR-11 `POST /stations/scribe/mcp`. A golden recall transcript plus contract tests fail on filesystem or ad-hoc HTTP freelance. Persona is not SKF-compiled. CFE untouched. No `pyforge.*` under `src/platform/`.

Files:
- `.claude/skills/bmad-agent-scribe/` — launcher SKILL.md, customize.toml, golden transcript
- `tests/meta/test_station_persona.py` — FR-38 contract
- `planning-artifacts/specs/spec-29-2-….md` — tracked story spec

Review: 2 low patches applied; follow-up score 2 → false.

Verification: 20 passed (`test_station_persona` + `test_skf_domain_skills`).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
