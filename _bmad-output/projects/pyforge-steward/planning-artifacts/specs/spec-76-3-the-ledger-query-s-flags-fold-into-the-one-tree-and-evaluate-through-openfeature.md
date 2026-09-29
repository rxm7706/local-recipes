---
title: "76.3: The ledger query's flags fold into the one tree and evaluate through OpenFeature"
type: 'feature'
created: '2026-09-28'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: flag-infrastructure
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/sprint_ledger_query.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/glass.py
  - src/shared/packages/pyforge-core/src/pyforge/core/flags.py
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - .claude/skills/bmad-sprint-ledger-query/SKILL.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** canopy:AD-11 says "Two trees is a review-blocking finding". Steward has a second one.
`sprint_ledger_query.eval_flag` (Story 65.1) resolves a flag from the CLI `--flag name=value` override, then the
`FLAGS_<NAME>` environment variable, then `<repo-root>/.steward/flags.json`, then a default, with no SDK. Six flags ride
it, all default off: `enable_postgres_sync`, `enable_dossier_export`, `enable_vizro_dataset`, `enable_herald_facts` and
`enable_jira_github_matrix` in `sprint_ledger_query.py`, and `enable_glass_export` in `glass.py` (Story 61.3), which
imports `eval_flag`. The Guild's Spec rules environment variables out as a provider and requires that `sprint_ledger_query`
evaluates through OpenFeature (`spec-feature-flag-governance` CAP-5).

**Approach:**

- The six flags become keys of the one tree, with `on` / `off` variants, `defaultVariant: off`, overlay values `off` in all
  three environments (today's behaviour), and Story 76.2's metadata (`owner: steward`; `story` the 65.1 or 61.3 ledger key;
  `created` the landing date; empty clock):
  `pyforge.steward.ledger_query_postgres_sync`, `pyforge.steward.ledger_query_dossier_export`,
  `pyforge.steward.ledger_query_vizro_dataset`, `pyforge.steward.ledger_query_herald_facts`,
  `pyforge.steward.ledger_query_jira_github_matrix`, `pyforge.steward.glass_export`.
- `pyforge.core.flags.read_boolean` (Story 75.1's reader, per-environment since Story 76.1) evaluates the rendered tree
  through OpenFeature's in-process FILE provider (`openfeature.contrib.provider.flagd`, `ResolverType.FILE`, as
  `django_pyforge.flags.configure_file_provider` does), importing OpenFeature function-locally. The four OpenFeature
  packages the platform features already pin (`openfeature-sdk`, `openfeature-flagd-api`, `openfeature-flagd-core`,
  `openfeature-provider-flagd`, `pixi.toml:242-245`, with their channel rule, canopy:AD-16) join the `pyforge-guild` and
  `pyforge-steward` features; the Guild's cold size is re-measured against CAP-5's 2 GB bound and recorded; `pixi.lock` is
  re-solved and `environment.yaml` regenerated. `steward keys exec`'s flag (Story 75.1) evaluates through it too.
- `eval_flag` reads each flag through `pyforge.core.flags.read_boolean`. The `FLAGS_<NAME>` layer and the
  `.steward/flags.json` path (`_FLAGS_RELATIVE_PATH`, `_default_flags_file`, the `flags_file_path` fallback) are removed.
- `--flag name=value` stays: an explicit per-invocation override that persists nothing and is not a provider. It accepts
  the tree keys; the old short names map to them through one table in `sprint_ledger_query.py`, so existing invocations in
  the skill keep working.
- A flag the reader cannot evaluate (OpenFeature absent, no tree) reads as off with a named WARN on stderr — the gated
  formatter refuses as it does today — never as on.
- `flag_off_message` names the tree key and how to turn it on (the overlay, or `--flag`).
- The two `pixi.toml` task descriptions that name `FLAGS_<NAME>` and `.steward/flags.json` (`sprint-ledger-query`,
  `sprint-ledger-postgres-sync`) are rewritten; `docs/how-to/pixi-tasks.md` follows;
  `.claude/skills/bmad-sprint-ledger-query/SKILL.md` documents the tree keys, and every Quick Invocation still runs verbatim
  (CAP-149).
- A steward meta-test reds any module under `src/pyforge/steward/` that reads `.steward/flags.json` or a `FLAGS_`
  environment variable.

Ledger key: `76-3-the-ledger-query-s-flags-fold-into-the-one-tree-and-evaluate-through-openfeature`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-76.1, S-76.2.

### Living CAP citations

- `spec-feature-flag-governance` CAP-5 ("Steward's `.steward/flags.json` folds into the one tree"; "`sprint_ledger_query`
  evaluates through OpenFeature"); its non-goal "environment variables as a provider".
- canopy:AD-11 (one tree; amended 2026-09-28).
- `spec-pyforge-steward` CAP-146..149 (Story 65.1's flags, the formatters they gate, CAP-149's verbatim-invocation rule);
  CAP-141 (Story 61.3's glass export).

## Acceptance Criteria

- Given the tree with the six keys off When each gated formatter (`static-dossier`, `herald-facts`, `atlas-dataset`, `sync-matrix`, `jira-csv`, `github-json`), the Postgres sync and the glass export run Then each refuses as today, naming its tree key, with exit codes unchanged
- Given two flagd trees, the key on and off When a gated formatter runs through `pyforge.core.flags` Then ON produces the payload and OFF refuses
- Given `FLAGS_ENABLE_DOSSIER_EXPORT=true` in the environment and the key off in the tree When `static-dossier` runs Then it refuses (the environment is no longer a provider)
- Given a `.steward/flags.json` turning a flag on and the key off in the tree When the formatter runs Then it refuses (the file is read by nothing)
- Given `--flag enable_dossier_export=true` or `--flag pyforge.steward.ledger_query_dossier_export=true` When `static-dossier` runs Then it produces the payload and writes nothing to any flag file
- Given OpenFeature absent When a gated formatter runs Then it refuses with a named WARN, never producing the payload
- Given the steward package When the meta-test runs Then no module reads `.steward/flags.json` or a `FLAGS_` variable
- Given the skill's Quick Invocations When each runs verbatim Then each succeeds or refuses exactly as documented
- Given a tree key on and off When `pyforge.core.flags.read_boolean` evaluates it Then OpenFeature's FILE provider produced the value (a test stubs the provider and sees it called), and it agrees with the host's evaluation of the same rendered tree
- Given `pixi run -e pyforge-guild python -c "import openfeature"` When it runs Then it exits 0, and the Guild's cold install stays under 2 GB, recorded in the story
- Given the change When `pixi run --frozen -e pyforge-steward pyforge-steward-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Read flags only through `pyforge.core.flags`; keep stdout payload-only and diagnostics on stderr (CAP-146..149).
- Keep `read_boolean`'s fleet-wide contract (Story 75.1: signature, resolution order, OFF/absent semantics, the Q3
  helpers) unchanged: OpenFeature replaces how a present key is evaluated, never what an absent or disabled one reads.
- Keep every gated formatter's exit code and refusal shape; only the source of truth changes.
- Reconcile every Spec `spec-surface-check` names (`spec-pyforge-core` for `pyforge-core`; the Specs that govern
  `pixi.toml` and `pixi.lock`), then stamp each scoped with `--spec`.
- `pixi.toml` and `pixi.lock` change: run `pixi run -e pyforge-guild pyforge-station-tests` before pushing; a Guild over
  2 GB stops the story (CAP-5's bound is never raised here).
- Edit `pixi.toml` and re-lock with `pixi lock`; never `pixi add` or `pixi update`.

**Never:**
- Do not keep an environment-variable or file layer "for compatibility"; that is the second tree this story removes.
- Do not turn any of the six flags on in any environment here.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| tree off | key `off` | formatter refuses, naming the key | exit as today |
| tree on | key `on` (test tree) | payload | — |
| env var set | `FLAGS_…=true`, tree off | refuses | — |
| stale file | `.steward/flags.json` on, tree off | refuses | — |
| CLI override | `--flag <short or tree key>=true` | payload; nothing persisted | — |
| no OpenFeature | reader unavailable | refuses | named WARN |

</intent-contract>

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-5 and its Non-goals, and the
`spec-pyforge-steward` memlog notes of 2026-09-28 (night) recording Epic 76's shape and the CLI reader.

## Binding

Parent Spec capability: `spec-feature-flag-governance` CAP-5 (the Guild's Spec; no station CAP or FR is minted).
Dream: `docs/dreams/feature-flag-governance.md`.
Ledger key: `76-3-the-ledger-query-s-flags-fold-into-the-one-tree-and-evaluate-through-openfeature`.
Ledger status at mint: `backlog`.
Deps: S-76.1 (the rendered tree the reader reads), S-76.2 (the metadata the six keys carry). Story 75.1, which adds the
reader, precedes 76.1.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- ON/OFF: the formatter tests write two flagd trees (key on, key off), the way
  `src/platform/tests/test_openfeature_file_flags.py` does, until the testing-kit fixture of `spec-feature-flag-governance`
  CAP-4 lands.
- `pixi run --frozen -e pyforge-guild pytest src/shared/packages/pyforge-core/tests/unit/test_flags.py -q` — expected: pass.
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (`pixi.toml` and `pixi.lock` changed).
- A cold `pixi install -e pyforge-guild` measured with `du -sm`, recorded against CAP-5's 2 GB bound.
- `pixi run --frozen -e pyforge-guild sprint-ledger-query -- --format static-dossier` — expected: refuses naming
  `pyforge.steward.ledger_query_dossier_export`; with `-- --flag pyforge.steward.ledger_query_dossier_export=true` it writes
  the payload.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings.

## Review Triage Log
