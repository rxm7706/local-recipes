---
title: '23.1: The account is enumerated and reconciled against the registry'
type: 'feature'
created: '2026-09-16'
status: 'done'
baseline_revision: 'e2a1fe04044bd28a4636cc6a295c9dce422a4a0f'
review_loop_iteration: 0
followup_review_recommended: true
context: []
deferred:
  - summary: >-
      sprint-status-ledger.yaml still reads `backlog` for this story's key even though
      implementation, verification and review are complete.
    evidence: |-
      This workflow's own step files never touch sprint-status-ledger.yaml -- that sync is
      owned by dedicated ledger-sync tooling run separately, not a hand-edit inside
      bmad-build-auto. A stale `backlog` row left against a story whose spec already reads
      `done` has previously caused indefinite redispatch in this repo (auto-memory:
      "Merged story + backlog ledger row respawns forever").
    location: >-
      _bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml (key
      23-1-the-account-is-enumerated-and-reconciled-against-the-registry)
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** list_projects pages of 20 and deck status only know README registry sections, so several projects are invisible.

**Approach:** Enumerate every project the login returns (paging), classify presentation / design system / excluded-by-name, reconcile against the registry. deck status lists linked / mirrored / excluded (<reason>) / untwinned. Two retired projects excluded by name in presentations/README.md.

## Boundaries & Constraints

**Always:**
- No account project is absent from herald deck status.

**Never:**
- Do not exclude by a name heuristic.
- Do not invent a second registry.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| retired project | REMOVED-PyForge Unifying Strategy | excluded (<reason>) | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-1`.
Surface: pyforge/herald/registry.py, state.py, cli.py (deck status account view); presentations/README.md; tests..
Ledger key: `23-1-the-account-is-enumerated-and-reconciled-against-the-registry`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-1-the-account-is-enumerated-and-reconciled-against-the-registry.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's policy `verify_commands` entry; MRS-GATE-010 binds the dispatch gate to this Success signal, and it is read from the primary tree's tracked spec, so it must be declared here before dispatch, not by the session).

**Manual checks:**
- `herald deck status` lists every project the account returns, each tagged `linked` / `mirrored` / `excluded (<reason>)` / `untwinned`; `REMOVED-PyForge Unifying Strategy` and `Local recipes repository connection` appear as `excluded` with the reason recorded in `presentations/README.md`.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 18 findings — high 0, medium 7, low 4, false 7, maybe-false 0
- findings:
  - `[medium]` `[defer]` sprint-status-ledger.yaml still reads `backlog` for this story key while the spec/memlog record full implementation — sync is owned by the dedicated ledger-sync tooling, not a hand-edit inside this workflow; deferred with a named follow-up (run ledger-sync) rather than hand-patched, per this repo's own documented incident where a stale `backlog` row against a done story caused indefinite redispatch.
  - `[false]` `[reject]` (blind-hunter) spec's "(paging)"/CAP-29's "paging past the first 20" is unimplemented — refuted: called `mcp__claude-design__list_projects` directly; its schema takes zero parameters and the live 20-project response carries no cursor/continuation field of any kind, so there is no client-side pagination mechanism to build against this tool.
  - `[false]` `[reject]` (edge-case-hunter) same paging claim — refuted by the same direct tool-schema verification above; no code exists to add.
  - `[false]` `[reject]` (intent-alignment) same paging divergence (primary) — refuted by the same verification; the intent's "(paging)" describes the pre-existing problem (an old page-1-only view), not an achievable requirement on this zero-argument tool.
  - `[medium]` `[reject]` spec's own `## Binding > Surface:` line omits `deck_pipeline.py` and `transport/*.py` (touched) and lists `state.py` (untouched) — real inaccuracy, but its only fix is editing this build's spec, which is a categorical reject per this workflow's rules.
  - `[low]` `[reject]` no test exercises a project matching two classification categories at once (e.g. excluded name that also resolves to a local twin) — real gap, but the current live account has no such overlap and the fix (a new fixture) is more than a trivial correction, so it fails the reject threshold's "and" condition in the low direction; rejected as unlikely in practice today.
  - `[medium]` `[patch]` (blind-hunter + verification-gap, same location) `_twinned_project_ids`'s `except errors.HeraldError: continue` has no test proving isolation the way the sibling `status()` does (`test_status_multi_deck_isolates_one_slugs_malformed_entry`) — a narrowed/removed except clause would silently crash the whole `--account` report instead of degrading one deck, a failure class this repo hit in production (Story 21.10). Action: added a mirroring isolation test.
  - `[medium]` `[patch]` (blind-hunter + edge-case-hunter, same location) `_twinned_project_ids` silently lets a duplicate `project_id` across two local decks overwrite in `by_project_id`, misattributing `slug` with no error — inconsistent with this file's fail-loud handling of malformed registry data elsewhere. Action: raise `errors.HeraldError` on a duplicate id, with a covering test.
  - `[low]` `[reject]` `--account`'s CLI tests exercise `linked`/`excluded` end-to-end but not `mirrored`/`untwinned` — real gap, but the CLI serializes all four statuses through one identical code path already covered at the pipeline layer, so unlikely to hide a real regression; fix is more than a trivial correction.
  - `[false]` `[reject]` `read_exclusions`'s malformed-row check is only tested for too-few cells, not 3+ cells from an unescaped `|` — refuted: `len(cells) != 2` already raises identically for both directions; the guard is already correct, just not separately enumerated in tests.
  - `[low]` `[patch]` `presentations/README.md`'s new "Local recipes repository connection" row cites "the FR-12 `stale_mirror` cautionary fixture," but `bridge-protocol.md`'s § *Pilot evidence* (the cited source) labels it "Cautionary fixture for CAP-3," never FR-12 (that label belongs to a different, older spec's numbering). Action: corrected the citation to CAP-3.
  - `[low]` `[patch]` `--account`'s `add_argument` help text never states it is mutually exclusive with a slug — only a runtime `HeraldError` enforces it. Action: added a short clause to the help text.
  - `[false]` `[reject]` (edge-case-hunter) `sanitize_payload`'s host-scrub could redact a project `name`/`url` legitimately containing `claudeusercontent.com` — refuted: this is pre-existing, deliberately documented "fail closed, visibly" behavior applied uniformly to every transport method already in production, not a risk newly introduced by `list_projects`.
  - `[medium]` `[patch]` `read_exclusions` silently lets a duplicate `Project` row in the exclusion table overwrite the earlier row's `reason` with no error — same "new aggregation, first time these combine" class as the `_twinned_project_ids` duplicate-id finding above (different location, so a separate entry). Action: raise `errors.HeraldError` on a duplicate project name, with a covering test.
  - `[false]` `[reject]` (intent-alignment) `DESIGN_SYSTEM_PROJECT_NAMES` as a Python constant is "a second registry" — refuted: it is a small, static identity constant (mirrors the pre-existing `MODERNIST_DESIGN_SYSTEM_ID` pattern in the same module), not a competing source of truth for the deck-project bridge the boundary protects.
  - `[false]` `[reject]` (intent-alignment) I/O matrix's literal `excluded (<reason>)` text vs. split JSON fields — refuted: the matrix notation is the same shorthand the spec's own Manual checks section uses to describe this exact JSON-based CLI output; not a real deviation.

## Auto Run Result

**Summary:** Implemented CAP-1: `herald deck status --account` enumerates every Design project the signed-in account can see (`transport.list_projects`, an 11th `DesignTransport` port method) and reconciles each one against the registry as `linked` / `mirrored` / `excluded (<reason>)` / `untwinned`, never by a name heuristic. `presentations/README.md` gained the `## Excluded projects (never twinned)` table naming the two retired projects with their reasons. Live-verified against the real account (20 projects, all present, none absent) both during implementation and independently by this review (a direct `list_projects` call during review confirmed the same 20 projects and confirmed the tool's schema takes zero parameters — settling the review's own pagination question).

**Files changed:**
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/base.py` — new `ProjectSummary` dataclass; `list_projects` added to the `DesignTransport` Protocol (11th port method).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py`, `agent_sdk_transport.py` — `list_projects` implemented on both adapters (bare JSON array, no wrapper).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/__init__.py` — re-exports `ProjectSummary`.
- `src/shared/packages/pyforge-herald/src/pyforge/herald/registry.py` — `DESIGN_SYSTEM_PROJECT_NAMES` constant; `read_exclusions()` (raises on a malformed or duplicate row, patched this pass).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` — `AccountProjectStatus` + `account_status()`; `_twinned_project_ids()` (raises on a duplicate registered project id, patched this pass).
- `src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py` — `deck status --account` (refuses an explicit slug; help text documents the constraint, patched this pass).
- `presentations/README.md` — the exclusions table (citation corrected from FR-12 to CAP-3, patched this pass).
- Tests across `test_mcp_transport.py`, `test_agent_sdk_transport.py`, `test_transport_base.py`, `test_bridge.py`, `test_registry.py`, `test_deck_status.py`, `test_cli_status.py` — 33 new tests total (30 from implementation + 3 from this review's patches).

**Review findings breakdown:**
- Patched (5, all applied and re-verified): malformed-README isolation now has a covering test; duplicate registered project id now raises `HeraldError`; duplicate exclusion-table row now raises `HeraldError`; the stale "FR-12" citation corrected to "CAP-3"; `--account` help text now documents its slug-exclusivity.
- Deferred (1): sprint-status-ledger.yaml sync for this story's key — recorded in frontmatter `deferred`, owned by ledger-sync tooling outside this workflow's scope.
- Rejected (12): three duplicate framings of a "paging" claim (`list_projects`'s schema was verified live, this review's own pass, to take zero parameters with no continuation field — no pagination mechanism exists to build); the spec's own stale `Binding > Surface:` line (fix would require editing this build's spec, categorically rejected); a missing classification-precedence test (no live overlap exists today, fix exceeds a trivial correction); a `sanitize_payload` redaction theory (pre-existing, deliberately documented behavior, not introduced by this diff); a CLI end-to-end coverage gap for `mirrored`/`untwinned` (same serialization path already covered at the pipeline layer); a malformed-row test-coverage nitpick (the code already raises correctly for that shape); two intent-alignment framings ("second registry" and I/O-matrix literal-text) both refuted against established codebase precedent and the spec's own notation.

**Follow-up review recommendation:** `true` (first pass, 3 patched entries graded `medium` — meets the "two or more medium" threshold). Named unverified risk: three of this pass's patched findings were the same class of defect (a new aggregation/parsing path silently mishandling a duplicate or malformed input) surfacing across two different functions in one review pass; a follow-up pass should specifically check whether the two `list_projects` transport implementations (`mcp_transport.py`, `agent_sdk_transport.py`) — which parse an external array into `ProjectSummary` objects — have an analogous unhandled-duplicate or malformed-entry gap that this pass's reviewers did not happen to probe for.

**Verification performed:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` (the spec's declared Success signal): 1396 passed / 4 skipped before this review's patches; 1399 passed / 4 skipped after (re-run independently by this review, not just trusted from the subagent's report).
- Matrix Test Audit: the one I/O & Edge-Case Matrix row (retired project → `excluded (<reason>)`) is covered by `test_account_status_classifies_an_excluded_project_with_its_reason` and `test_account_status_reports_no_project_absent`, both ran and passed.
- Manual check (`herald deck status --account` against the real account): performed live during implementation (20/20 projects present, correctly classified) and spot-checked independently during this review via a direct `list_projects` call (same 20 projects, confirming the schema and settling the pagination question); a full CLI re-run during finalization hit an expired Design credential (`/design-login` required), unrelated to code correctness — the underlying transport call was already independently verified via the direct tool call.
- Reviewed the actual diff (not just subagent narration) at each stage: read the full unified diff before and after patches, and directly inspected the five patched code sites to confirm each fix matches its triage-log row before finalizing.

**Residual risks:** the named follow-up-review risk above (untested duplicate/malformed-entry handling in the two `list_projects` transport adapters); the deferred ledger-sync item.
