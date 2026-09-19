---
title: '19.2: scribe capture and recall run from the session default environment'
type: 'feature'
created: '2026-09-19'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md']
deferred:
  - summary: "Recall over the station MCP (`/stations/scribe/mcp`) so a harness that cannot run pixi at all (a hosted agent with only HTTP tool access) can still ask team memory — Dream item (7), the second half. The Guild-env half landed here."
    evidence: "Copilot cloud agent sessions have a 59-minute cap and only what `copilot-setup-steps.yml` installs; Devin sessions boot from a machine snapshot. Both can run pixi; a pure-MCP consumer (Claude Design, a hosted reviewer) cannot."
    location: src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py
    severity: low
declared_low_risk: true
baseline_revision: '1ff4b6d212084d74e3be6112221a4261822d74f0'
final_revision: 'pending — the merge commit of PR #1513'
---

<intent-contract>

## Intent

**Problem:** `pyforge-guild` is the default environment for every harness (steward Story 63.1,
`spec-pyforge-steward` CAP-5) — the Claude Code remote hook, Cursor Cloud's `environment.json`,
Copilot's `copilot-setup-steps.yml` all install it and nothing else — but the scribe CLI lived only
in `-e pyforge-scribe`, so those sessions could neither `scribe capture` a decision nor
`scribe recall` one. Every governance doc told them to use an environment they did not have.

**Approach:** add the scribe **core** package (run-deps `typer`, `pydantic`, `pyforge-core`) to
`[feature.pyforge-guild.dependencies]`; leave the heavy compile extras (`graphifyy`, `cocoindex`,
`psycopg`) in `-e pyforge-scribe`; repoint the docs; pin it with a meta-test.

## Boundaries & Constraints

**Always:** one path dependency, no extra; `environment.yaml` (the `build` env) unchanged; the
extras stay per-env (AD-6 air-gap; the `feature.pyforge-guild` comment).
**Never:** add `graphifyy` / `cocoindex` / `psycopg` to the Guild default.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| `pixi run -e pyforge-guild scribe --help` | lists `capture`, `recall`, `graph` |
| `pixi run -e pyforge-guild scribe graph compile --surface graphify` | refuses: the extra is not installed here (unchanged behaviour of the lazy import) |
| `pyforge-scribe` removed from the Guild feature | `test_scribe_core_is_a_guild_feature_dependency` reds |
| a doc says `-e pyforge-scribe scribe recall` again | `test_governance_docs_no_longer_route_capture_or_recall_to_the_scribe_env` reds |
| `pixi lock` after the change | `pixi.lock` gains the `pyforge-scribe` conda source for the `pyforge-guild` and `default` envs; `llms-full-check` stays green (no new versioned dep) |

## Code Map

- `pixi.toml` — `[feature.pyforge-guild.dependencies]` `pyforge-scribe = { path = … }` with the extras caveat; the `feature.pyforge-guild` header comment corrected.
- `pixi.lock` — re-locked (`pixi lock`), +196 lines: the scribe conda source in `pyforge-guild` / `default`.
- `AGENTS.md` (§ *Scribe recall*, § *Team memory*, § *Library catalog*), `CLAUDE.md` (§ Common Commands), `.cursor/rules/scribe-recall.mdc` — invocations on `-e pyforge-guild`.
- `src/shared/packages/pyforge-scribe/tests/meta/test_guild_env_membership.py` — 8 tests.

## Binding

Parent Spec capability: `spec-pyforge-scribe CAP-28`.
Ledger key: `19-2-scribe-capture-and-recall-run-from-the-session-default-environment`.
Ledger status: `done`.

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** `spec-pyforge-scribe` CAP-28
**Given** the Guild default carries no scribe CLI **When** this story lands **Then** `scribe capture` / `recall` run in `-e pyforge-guild`, the extras stay per-env, the docs say so, a meta-test pins it.
**Status:** done

</intent-contract>

## Review Triage Log

### 2026-09-19 — Review pass (single-CAP fix, operator-directed)
- patch: 1 — the `feature.pyforge-guild` comment ("Scribe recall stays `-e pyforge-scribe`") and `AGENTS.md` § *Library catalog* still told sessions the old routing after the dependency was added; both corrected and the meta-test now reads the docs.
- defer: 1 — the MCP half (frontmatter).
- reject: 0.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass.

**Manual checks:** `pixi run --frozen -e pyforge-guild scribe --help` → exit 0 with `capture` / `recall` / `graph`; `pixi project export conda-environment -e build | diff - environment.yaml` → empty; `pixi run -e pyforge-guild llms-full-check` → exit 0; `pixi run -e pyforge-guild pyforge-station-tests` (pixi.toml / pixi.lock changed → all eight stations + core).

## Auto Run Result

- **Summary:** one path dependency added to the Guild feature, lock re-solved, three governance docs repointed, an 8-test meta-test added; `scribe --help` verified in the worktree's freshly installed `pyforge-guild`.
- **Verification (exit codes read directly, 2026-09-19):** filled in at landing — see the PR.
