---
title: "113.1: marshal factory challenge runs a fresh-context review of one chain artifact"
type: 'feature'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.marshal.egm_challenge
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "the verb stays listed and refuses with the usage code before any spawn; no report, no journal entry, no reviewer session"
  cleanup: "90 days after ON in every environment (Q4); the date is set when the switch turns ON everywhere"
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/glossary.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/reference/story-spec-flag-block.md
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
---

<intent-contract>

## Intent

**Problem:** the chain has two verifiers and both are blind the same way. The detectors count ids and hashes and never read; the `bmad-review` lenses read with `CLAUDE.md`, `AGENTS.md` and the memory index already loaded, so a wrong idea the whole house shares is invisible to both. Nothing on the floor can read a Spec, a story spec or a rules file cold and say what is assumed but never written.

**Approach:**
- A new duty `marshal factory challenge --project <station> --target <path> --stage {mint,decompose,readiness,drift,rules}` launches one harness session through the existing seam (as dispatch does) whose only task is to spawn the EGM plugin's registered reviewer agents for the stage (`egm:egm-zoom-out`, `egm:egm-design`, `egm:egm-comprehension`, `egm:egm-implementation-readiness`, `egm:egm-codebase-details`, `egm:egm-synthesizer`, as the stage selects) and to write their flat deficiency report. Marshal never invokes an EGM `Skill` (every EGM `SKILL.md` is `disable-model-invocation: true`) and never makes a model call itself.
- The report lands under Tier 3 `_bmad-output/projects/<station>/implementation-artifacts/egm/<run>/`; the run is journaled beside the dispatch runs with an intent entry before the first spawn and an outcome after the last, the report path on the run record.
- Exit 0 whatever the findings say: findings are data, never a verdict. The verb's own refusals — plugin absent, plugin not at the version `.claude/settings.json` pins, switch off, bad policy block — project through the one exit-code owner as the usage code; no new exit code is minted (the Spec's 2026-11-01 open question stays open).
- The plugin pin lands here: `.claude/settings.json` `enabledPlugins` gains `egm@egm` and `extraKnownMarketplaces` the `google/elephant-goldfish-model` marketplace, and the claude harness profile's dispatch `--settings` gains the headless `Read(...)` rules on the plugin cache's `agents/`, `docs/`, `resources/` and `skills/` folders, version segment `*`.
- Which personas a stage spawns, and with which context, comes from Story 113.2's `[challenge]` block; until that lands the verb ships a built-in default group per stage and the goldfish context rule of CAP-299 (target, `glossary.md`, cited Dream entry, stage standard; never `AGENTS.md`, `CLAUDE.md`, a memlog, a URL or session text).

Ledger key: `113-1-marshal-factory-challenge-runs-a-fresh-context-review-of-one-chain-artifact`.
Type / Effort / Deps: feature / L / none.

### Living CAP citations

- **`spec-pyforge-marshal` CAP-298** — the capability this story realizes: one verb, five stages, Tier-3 report, journal, exit 0, plugin-absent refusal, kill switch.
- **CAP-299** — the goldfish context rule the built-in default group obeys until Story 113.2 lands the policy block.
- **`spec-feature-flag-governance:CAP-1`** — the flag block; Q3 (a flag-off verb stays listed and refuses with the usage code), Q4 (the 90-day clock), Q6 (one flag per CAP).

## Acceptance Criteria

- **AC1 — The key.** `pyforge.marshal.egm_challenge` is in `src/platform/config/flags.json` (`defaultVariant: off`) and in every environment of `flag-overlays.json` (`off`), with `owner`, `story`, `created` 2026-11-01 and the clock fields; `test_flags.py`'s shipped-flag tables name it; `flag-inventory` lists CAP-298 against it.
- **AC2 — ON.** With the key on, the plugin pinned and present, and a `--stage` given, the verb spawns the stage's reviewer group through the harness session, writes one flat deficiency report under `implementation-artifacts/egm/<run>/`, journals intent and outcome, and exits 0 — including when the report lists findings.
- **AC3 — OFF.** With the key off the verb stays listed and refuses with the usage code before any spawn; nothing is written.
- **AC4 — Refusals.** Plugin absent, or the cache version not the one `.claude/settings.json` pins, refuses with the usage code before any spawn; the refusal reason is in the journal.
- **AC5 — Both states.** One test runs the key ON and OFF (`src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py`), with the harness session stubbed; a second test pins the refusal paths.
- **AC6 — The pin.** `.claude/settings.json` enables `egm@egm` and its marketplace; the version pin is `[challenge].plugin_version` (default `0.1.0`), checked against Claude Code's `installed_plugins.json` and the cache manifest; the challenge session's own `--settings` carries the four `Read(...)` rules on the plugin cache with `*` for the version segment, read-only tools plus `Agent`, one `Write` rule confined to the run folder and an explicit deny list, under `--permission-mode default`; tests assert both.
- **AC7 — The domain.** The station's frozen exit-code domain is unchanged: every refusal is the usage code 2, a session that fails or writes no valid report is unevaluable (1); marshal counts no factory sub-verbs, so no count assertion moves.

## Boundaries & Constraints

**Always:**
- Launch reviewers through the one harness seam; read the report back as data; pass absolute paths and never URLs.
- Read the key only through `pyforge.core.flags`; spell it literally at the read site.

**Never:**
- Never make a model call from Marshal; never invoke an EGM skill through `Skill`; never pass `AGENTS.md`, `CLAUDE.md`, a memlog or session text to a reviewer; never mint a new exit code; never write a ledger, a `SPEC.md` or a story spec's `status`; never run `egm-bootstrap`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-marshal` CAP-298.

Parent: `spec-pyforge-marshal` CAP-298

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-11-01 (A stranger reads the chain) entry.
- Epic: Epic 113, minted with this story.
- Ledger key: `113-1-marshal-factory-challenge-runs-a-fresh-context-review-of-one-chain-artifact`.
- Deps: none.
- Surface: `marshal-policy.toml` `[epic_surfaces]."113"`.
- Minted 2026-11-01 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).

**Run before the push:**
- Two-state flag coverage (the testing kit's `flag_states`): `src/shared/packages/pyforge-marshal/tests/unit/test_factory_challenge.py` — `@flag_states("pyforge.marshal.egm_challenge")`.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0; the row names this story's key.
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass (`test_flags.py`'s shipped-flag tables).

## Auto Run Result

Status: done

Summary: built by hand in the single Epic 113 PR (2026-11-01, operator direction: one PR, the 113.1 dispatch stopped before any push); independently reviewed, review findings fixed.

## Spec Change Log

- 2026-11-01: minted from the station Dream's entry of 2026-11-01 (EGM challenger) at the operator's direction: full integration, everything reversible and behind flags, ad hoc or integrated, a one-time audit.
- 2026-11-01: built. Deviations (Spec memlog, 2026-11-01): the version pin lives in `[challenge].plugin_version` because `enabledPlugins` carries no version; the plugin-cache Read rules sit in the challenge session's own `--settings` (`adapters/challenge_harness.py`), never in `claude.toml`'s shared dispatch argv; the challenger always runs on the packaged claude profile; the design-critic agent is `egm:egm-design`; review fixes add the adapter isolation check (`omitClaudeMd`, read-only tools), the installed-version check, a journaled refusal, a working-tree change check and a restricted orchestrator session.

## Review Triage Log

- 2026-11-01: independent review (fresh subagent, read the diff against this spec) returned FAIL with blockers B1 (two named test files absent) and B2 (the audit refused six stations with no glossary) and should-fix S1-S11; every finding was fixed in the same PR except S7 (`marshal watch` display), recorded as DW-marshal-113-3-1. See the Spec memlog's 2026-11-01 review entry.
