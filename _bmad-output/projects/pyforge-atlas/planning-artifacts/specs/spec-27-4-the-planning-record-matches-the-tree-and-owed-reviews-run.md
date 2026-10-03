---
title: "27.4: The planning record matches the tree, the cross-station seams hold, and the owed follow-up reviews run"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 24 open deferred-work rows (7 medium, 17 low) that sit in Atlas's planning record, at its seams with other stations, or in reviews it still owes: DESIGN.md's page count disagrees with `PAGE_INVENTORY`; 27 per-story `Status:` lines in epics.md read `backlog` against `done` ledger rows; catalog-sources.md names an entry that was never built; the ledger's Provenance prose describes a 52-entry ledger; two entries are still cut at 500 characters by the pre-fix intake tool; nothing checks that a closed row's `verified:` citation points at a real file and line; steward's adoption-register test passes on a bare skill-name substring; the vendored design-thinking template renders an unresolved `{{project_name}}`; and eight landed stories (10.5, 10.6, 12.3, 16.1, 19.1, 20.2, 20.3, 20.4) still carry a recommended follow-up review that never ran.

**Approach:** Reconcile the planning documents to the tree and pin each with a test; restore the truncated entries from their source specs' `deferred:` frontmatter; add an atlas meta-test that resolves every closed row's cited `path:line`; tighten steward's `_persona_mentions`; resolve the template placeholder through the sanctioned `_bmad/custom/` override; then run the eight follow-up reviews against the tree Stories 27.1-27.3 leave, record each in its story spec, and fix what they find.

Ledger key: `27-4-the-planning-record-matches-the-tree-and-owed-reviews-run`.
Type / Effort / Deps: fix / L / S-27.1, S-27.2, S-27.3.
Rows: 24 (7 medium, 17 low).

### Living CAP citations

- The atlas capabilities that shipped each behaviour (see each row's source story); a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given DESIGN.md, epics.md and the tracked ledger When the new planning tests run Then DESIGN.md's page count matches `PAGE_INVENTORY` and every epics.md `Status:` line matches its ledger row, and each test fails on a seeded disagreement
- Given atlas's tracked ledger When the citation meta-test runs Then every closed row's `verified:` `path:line` names a tracked file with at least that many lines, and a fabricated citation fails it
- Given a persona SKILL.md that names `mcp-builder` but has lost its routing-constraint sentence When steward's adoption-register test runs Then it fails
- Given the design-thinking skill rendered through its `_bmad/custom/` override When its template is filled Then the title carries the configured project name
- Given each of the eight owed follow-up reviews When it has run Then its findings are recorded in that story spec's Review Triage Log and each finding is fixed in this story
- Given each defect this story fixes When its new test runs against the tree before the fix Then it fails, and after the fix it passes
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-20-4-2`, `DW-FU-20-4-5`, `DW-FU-20-4-4`, `DW-FU-20-4-7`, `DW-FU-21-8-6`, `DW-FU-21-8-11`, `DW-FU-24-1`, `DW-FU-20-2`, `DW-FU-20-4`, `DW-FU-21-5-2`, `DW-FU-21-5-4`, `DW-FU-21-8-7`, `DW-FU-20-4-3`, `DW-FU-20-4-6`, `DW-FU-24-1-2`, `DW-FU-13-3`, `DW-13-3-7`, `DW-10-5-9`, `DW-10-6-4`, `DW-FRR-16-1`, `DW-FRR-19-1`, `DW-FRR-20-2`, `DW-FRR-20-3`, `DW-FRR-20-4` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Run each follow-up review as an independent pass (blind and edge-case layers) against the current tree, never the original implementer's summary (AGENTS.md § Behavioural guidelines item 8). Reconcile every Spec the spec-surface detector names when steward's test file moves (`spec-pyforge-steward` co-governs it). Fix each defect where the shipped behaviour lives now and pin it with a test that fails without the fix. A re-ingested twin closes with the row it repeats, citing the same fix.

**Never:** Never edit an installer-owned file under `.claude/skills/bmad-cis-design-thinking/`; the override lives in `_bmad/custom/`. Never open an upstream issue or pull request against the CIS package without the operator's explicit ask. Never close a review row before its review has run and its findings are fixed. Never close a row without a landed fix and a cited `verified:` line (no blanket closure).

</intent-contract>

## Deferred-work rows this story closes (operator ruling 2026-10-03, deferral burn-down Phase 4+5)

- `DW-FU-20-4-2` (medium) — DESIGN.md § 0 and § 6 reconcile the page count with `PAGE_INVENTORY` as shipped (21 unaddressed CLI questions, the one consolidation, the non-CLI pages named); a test compares DESIGN.md's count table with `PAGE_INVENTORY`.
- `DW-FU-20-4-5` (medium) — Re-ingested twin of `DW-FU-20-4-2` (same text, later intake); closed by the same fix and test.
- `DW-FU-20-4-4` (medium) — An atlas meta-test checks that every closed row's `verified:` `path:line` in atlas's ledger names a tracked file with at least that many lines. Doctor Story 38.1 already requires the citation (`_verified_line_cites`); this checks it is real. The done-key half is story-status-check's landing evidence, cited.
- `DW-FU-20-4-7` (medium) — Re-ingested twin of `DW-FU-20-4-4` (same text, later intake); closed by the same fix and test.
- `DW-FU-21-8-6` (medium) — Doctor has fixed `_flatten_deferred_scalar` (it now marks a truncation and gives the full length); this story restores atlas's entries the pre-fix tool cut at 500 characters (`DW-FU-21-3-7`, `DW-FU-21-5-2`) from their source specs' `deferred:` frontmatter, and cites the doctor fix.
- `DW-FU-21-8-11` (medium) — Re-ingested twin of `DW-FU-21-8-6` (same text, later intake); closed by the same fix and test.
- `DW-FU-24-1` (medium) — steward's `_persona_mentions` (`tests/meta/test_adoption_register.py`) checks the register row's routing-constraint text in the persona SKILL.md, not a bare skill-name substring.
- `DW-FU-20-2` (low) — Every per-story `Status:` line in epics.md is reconciled to its ledger row (27 read `backlog` against `done` rows today), and a test fails when one disagrees.
- `DW-FU-20-4` (low) — Closed by the same reconciliation and test as DW-FU-20-2 (Stories 19.4 and 19.5 under today's numbering).
- `DW-FU-21-5-2` (low) — catalog-sources.md's Tier 2 row names `enterprise_jfrog_names` under `upstream_discovery`, as built.
- `DW-FU-21-5-4` (low) — Re-ingested twin of `DW-FU-21-5-2` (same text, later intake); closed by the same fix and test.
- `DW-FU-21-8-7` (low) — The ledger's Provenance prose states the current entry counts, as the counting test derives them.
- `DW-FU-20-4-3` (low) — `_bmad/custom/bmad-cis-design-thinking.toml` adds an `activation_steps_append` step that resolves `{{project_name}}` from `_bmad/core/config.yaml` (the skill's `customize.toml` admits it); a test pins it. Reporting the bug upstream is outward work and needs the operator's ask.
- `DW-FU-20-4-6` (low) — Re-ingested twin of `DW-FU-20-4-3` (same text, later intake); closed by the same fix and test.
- `DW-FU-24-1-2` (low) — Confirm the pull request that landed Story 23.1 carried the `maintenance` label (`gh pr view <n> --repo rxm7706/local-recipes --json labels`) and close citing that command and its exit code.
- `DW-FU-13-3` (low) — Run the follow-up review of Story 12.3 (`spec-12-3-trending-candidates-operator-surface-fr-66.md`); one review closes this row and DW-13-3-7.
- `DW-13-3-7` (low) — Same owed review as DW-FU-13-3 (Story 12.3); closed by it.
- `DW-10-5-9` (low) — Run the follow-up review of Story 10.5 (`spec-10-5-stamp-advisory-data-with-its-build-provenance-2.md`).
- `DW-10-6-4` (low) — Run the follow-up review of Story 10.6 (`spec-10-6-make-run-admission-real-or-stop-claiming-it.md`).
- `DW-FRR-16-1` (low) — Run the follow-up review of Story 16.1 (`spec-16-1-the-from-scratch-run-is-a-chartered-capability.md`).
- `DW-FRR-19-1` (low) — Run the follow-up review of Story 19.1 (`spec-19-1-one-boot-script-raises-both-plane-faces-cap-5.md`).
- `DW-FRR-20-2` (low) — Run the follow-up review of Story 20.2 (`spec-20-2-remove-cf_atlas-db-seeds-from-production-datasets.md`), against the code Story 27.2 leaves.
- `DW-FRR-20-3` (low) — Run the follow-up review of Story 20.3 (`spec-20-3-tier-0-harden-and-live-catalog-contract.md`), against the code Story 27.1 leaves.
- `DW-FRR-20-4` (low) — Run the follow-up review of Story 20.4 (`spec-20-4-tier-1-catalog-sources-selfexplainml-anaconda-basilisk-aoss.md`), against the code Story 27.2 leaves.

## Binding

Parent: The atlas capabilities that shipped each behaviour; a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag.
Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `27-4-the-planning-record-matches-the-tree-and-owed-reviews-run`.
Ledger status at mint: `backlog`.
Deps: S-27.1, S-27.2, S-27.3.
Surface: `planning-artifacts/DESIGN.md`, `planning-artifacts/epics.md` (per-story `Status:` lines only), `planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md`, the atlas deferred-work ledger, `src/shared/packages/pyforge-atlas/tests/meta/` (the planning and citation tests), `src/shared/packages/pyforge-steward/tests/meta/test_adoption_register.py`, `.claude/skills/bmad-agent-atlas/SKILL.md`, `_bmad/custom/bmad-cis-design-thinking.toml`, the eight reviewed story specs' Review Triage Logs, and whatever atlas code a review finding fixes.
Minted 2026-10-03 from the operator's Phase 4+5 ruling (open medium and low deferrals fixed together, split by package area, at most about 30 rows per story).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
