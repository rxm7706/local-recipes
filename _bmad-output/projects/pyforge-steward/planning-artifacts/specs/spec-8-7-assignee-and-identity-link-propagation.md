---
title: 'Assignee and identity-link propagation (Epic 8 Story 8.7, pyforge-steward)'
type: 'feature'
created: '2026-08-15'
status: 'done'
blocking_condition: ''
baseline_revision: '51262819e76bde4d19c9511b20925e815b1c0503'
final_revision: '6d5d748d48a1c9b877d20c9d2f8e2944b85ef03b'
preserved_ref: 'attempt-preserve/8-7-assignee-and-identity-link-propagation-intentgap'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-8-6-explicit-status-vocabulary-translation.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** CAP-1 promises "status, assignee, and identity link" propagate bidirectionally, but
Story 8.1's frozen contract deliberately narrowed delivery to status-only, leaving assignee and
the identity link undelivered with no owning story (audit finding AF-5). Today an operator must
manually type BOTH sides' link-field values before `reconcile()` will run at all, and
`SyncConfig.user_mapping` (GitHub login -> Jira accountId) is loaded but never consulted.

**Approach:** Add `"assignee"` as a second tracked field alongside `"status"` in `reconcile()`,
using the exact same per-field baseline/AD-4-authority mechanism, translated through
`user_mapping` (and its computed inverse). Separately, self-heal the identity-link field: once a
pair is resolved via either side's existing link, write the missing/stale side's link value
unconditionally -- this is NOT baselined like status/assignee (its correct value is always an
independently known constant, `jira.issue_key`/`gh.item_id`, never a "which side wins" decision).

## Boundaries & Constraints

**Always:**
- Assignee follows status's exact decision shape (baseline-vs-current per side, AD-4 conflict ->
  GitHub wins unless `field_overrides["assignee"] == "jira"`) -- extend `_VALID_OVERRIDE_FIELDS`
  to `("status", "assignee")`.
- GitHub's assignee is native to the underlying Issue/PR (`ProjectV2Item.content`), never a
  custom Projects V2 field -- extend `_GET_PROJECT_ITEM_QUERY` with
  `content { ... on Issue { number assignees(first: 10) { nodes { login } } repository { owner
  { login } name } } ... on PullRequest { <same> } }`. A `content` that is a genuine `DraftIssue`
  (or absent, e.g. every pre-8.7 test fixture) reads as `gh.assignee = None`, `content_ref =
  None` -- valid "no assignee" state, never an error. **RESOLVED 2026-08-15 (escalation, finding
  3):** this is DISTINCT from an UNREADABLE `content` (a populated `errors` array, or a shape
  that is neither a clean `DraftIssue`/`Issue`/`PullRequest`, e.g. a permission gap on a
  Projects-only token) -- an unreadable `content` reads as `gh.assignee = UNKNOWN`, never `None`,
  and the assignee decision for that tick downgrades to `no_op` (skip; never write, never clear
  either side; re-attempted next tick). Only a genuine `DraftIssue` or a confirmed-empty
  `assignees` list on a real `Issue`/`PullRequest` is "no assignee." **RESOLVED (escalation,
  finding 4):** `assignees(first: 10).nodes` with length > 1 (an untracked co-assignee exists) is
  refused named (`SyncMultipleAssigneesError`) rather than silently tracking only the first --
  never guess which login is "the tracked one."
- Write GitHub's assignee via REST (`POST`/`DELETE
  https://api.github.com/repos/{owner}/{repo}/issues/{number}/assignees`, body
  `{"assignees": [login]}`), not GraphQL -- avoids a second login-to-node-ID resolution call.
  Remove ONLY the previously-tracked login (from baseline), add ONLY the new one -- never touch
  an assignee this module didn't itself add.
- Write Jira's assignee via the EXISTING `update_jira_issue_fields` (`{"assignee": {"accountId":
  v}}` or `{"assignee": None}` to clear) -- no new Jira-side plumbing. Add `"assignee"` to
  `get_jira_issue`'s `requested_fields` string.
- `user_mapping` (github login -> jira accountId) translates push_to_jira directly; its computed
  inverse (`{v: k for k, v in user_mapping.items()}`) translates push_to_github. An explicit
  `None` (unassigned) bypasses translation on either direction (mirrors `status_mapping`'s
  None-bypass precedent, `sync.py:993-997`). A non-null value absent from the relevant direction
  raises a new `SyncUnmappedUserError(SyncError)` -- caught by the existing `except SyncError`
  handling, zero new plumbing, mirrors `SyncUnmappedStatusError` exactly.
- `load_config` type-checks `user_mapping`'s keys/values as strings (mirrors `status_mapping`'s
  Story-8.6 check, `sync.py:199-209`) -- closes this story's own now-load-bearing deferred item
  (`deferred-work.md`, the un-ID'd "`user_mapping` values aren't type-checked" entry, filed
  low-impact specifically because the field was unused; it is unused no longer).
- Identity-link repair: once `gh`/`jira` are resolved (via any of `_read_both_sides`'s three
  existing paths), compute `gh.link != jira.issue_key` and `jira.link != gh.item_id`
  independently; write whichever side doesn't already match, unconditionally, no baseline
  entry, no AD-4 involvement (both sides' correct values are simultaneously and independently
  knowable -- this is a dual self-heal, not a "which side wins" conflict).
- The three existing `_read_both_sides` hard-fail cases (`sync.py:840-841`, `:847-848`,
  `:853-861`) are preserved EXACTLY: (a) a single-identifier call whose own driving side has no
  link value still raises `SyncUnlinkedError` immediately (there is nothing to resolve the pair
  from); (b) both sides already carrying a non-empty, non-matching link still raises
  `SyncUnlinkedError` ("not a reciprocal pair") -- never silently overwritten. Only the
  previously-hard-failing "one side already resolved to a link, the other side's OWN link field
  reads empty" case (the literal AF-5 gap) becomes a repair instead of a failure.
- The true no-op fast path (`sync.py:919-936`) requires status AND assignee unchanged on both
  sides AND zero pending link repairs before returning with zero writes.
- Field writes proceed in order (status, then assignee, then link repairs); a `SyncError` from
  any step returns immediately (`ok=False`), matching the existing accepted non-atomicity
  precedent -- never attempts a later field after an earlier one failed.
- The merged baseline write (one `update_project_item_field`/`update_jira_issue_fields` call per
  side, unchanged call count) always includes BOTH `"status"` and `"assignee"` keys whenever
  triggered for any reason -- this is how a pre-8.7 item's first post-upgrade reconcile silently
  backfills its missing `"assignee"` baseline key at zero extra API cost, the moment any OTHER
  field's divergence already triggers a write. `--dry-run` reports both fields' computed
  decisions and any pending link repairs; makes zero writes (unchanged early-branch shape).
- `SyncConfig`'s schema is UNCHANGED -- no new required field. Assignee needs no field ID
  (native, not custom); the link field IDs already exist. An operator's existing
  `.steward/sync-config.yaml` needs no edits to pick up this story.

**Block If:** none identified. This run's environment has no live GitHub Projects V2 board, no
live Jira Cloud project, and no credentials for either -- expected for an unattended build of an
external-system integration (Story 8.1's own precedent), handled as an operator-executed manual
verification step, not a mid-build halt. The `content { ... on Issue { assignees ... } }`
GraphQL shape and the `/issues/{number}/assignees` REST endpoint's exact response shape are
grounded in GitHub's documented public schema but unverified against a LIVE board this session
(same category as `_GITHUB_BASELINE_FIELD_CEILING`'s own "conservative, explicitly unverified"
precedent, `sync.py:304-308`) -- re-verify at implementation/manual-verification time rather than
treating the query/mutation shapes as certain.

**Never:**
- Never manage a GitHub item carrying more than one assignee -- **RESOLVED (escalation, finding
  4, decision (a)):** `assignees(first: 10).nodes` with length > 1 refuses the item named
  (`SyncMultipleAssigneesError`, no write to either side) rather than reading/tracking only the
  first node and risking a two-assignee or silent-revert corruption on a later tick. Never remove
  an assignee this module did not itself add via its own tracked baseline entry.
- Never attempt an assignee write against a GitHub item whose `content` is a `DraftIssue` (no
  `owner`/`repo`/`number` to target) -- raise `SyncAPIError` naming the item; never guess a
  target. Never treat an UNREADABLE `content` (distinct from a genuine `DraftIssue`) as an
  authoritative unassignment -- see the Always list's finding-3 resolution; it downgrades to
  `no_op`, never a destructive write.
- Never write `"assignee"` for the `push_to_jira`/`push_to_github` no_op case beyond what the
  existing convergence check (`sync.py:951-960`) already downgrades -- assignee's convergence
  check is a direct, exact duplicate of that same logic, not a new mechanism.
- Never baseline the identity-link field, and never route it through `field_overrides`/AD-4 --
  its correctness condition is stateless (always independently derivable from the resolved
  pair), unlike status/assignee's genuinely mutable, history-dependent values.
- Never auto-provision the GitHub/Jira link fields themselves (unchanged from Story 8.1) --
  their existence is still an operator-supplied `SyncConfig` precondition; this story only
  writes VALUES into fields that already exist.
- Never change `--schedule`'s candidate-discovery mechanism (`list_linked_github_items`) -- link
  repair only applies to a pair `reconcile()` has already resolved by SOME means; a
  wholly-unlinked item is still only discoverable via GitHub's own link field, unchanged.
- **RESOLVED 2026-08-15 (escalation, findings 1+2):** a missing `"assignee"` baseline key on an
  established pair is a first-sync decision for THAT FIELD, exactly like a wholly-new pair --
  never a silent, un-compared adoption. The two sides' current assignee values ARE compared on
  first observation and AD-4 decides exactly as it would for a genuinely new pair (GitHub wins
  unless `field_overrides["assignee"] == "jira"`); the decided value is written to whichever
  side needs it, and the write IS what backfills the baseline going forward. This supersedes the
  prior "silently adopted, never propagated, never flagged" behavior -- a real write now occurs
  the first time a pre-8.7 pair is observed with mismatched assignees, precisely once per pair
  (never a recurring write-storm; only a real, then-current divergence triggers it). Success is
  tracked PER FIELD, not derived from the pair's overall baseline truthiness (finding 2): a
  status write succeeding on the same tick an assignee write fails must never retroactively mark
  assignee "established" -- each field's own persisted baseline is the only source of truth for
  whether THAT field has been observed.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Assignee changed on GitHub only | `gh.assignee="octocat"` differs from baseline; jira unchanged | Translated via `user_mapping`, written to Jira's `assignee.accountId`; both baselines record the field | No error expected |
| Assignee changed on Jira only | inverse of above | Translated via `user_mapping`'s inverse, GitHub REST add/remove issued; both baselines updated | No error expected |
| Assignee value unmapped in the needed direction | e.g. github login has no `user_mapping` entry | `ok=False`, no write to either side, item fails named (matches AD-6) | `SyncUnmappedUserError`, greppable |
| Assignee explicitly cleared on one side | value becomes `None` | Bypasses translation; other side's assignee cleared (Jira: `{"assignee": None}`; GitHub: remove tracked login only) | No error expected |
| GitHub content is a DraftIssue, assignee push targeted at it | `content_ref is None` | No write attempted; named failure | `SyncAPIError`, never a guess |
| Identity link missing on exactly one side | `gh.link="PROJ-1"`, `jira.link=""` (resolved via GH) | Jira's link field auto-written to `gh.item_id`; no human action; not baselined | No error expected |
| Identity link populated but mismatched on both sides | `gh.link="PROJ-1"`, `jira.link="ITEM_999"` | Unchanged from Story 8.1: hard fail, no write to either side | `SyncUnlinkedError`, "not a reciprocal pair" |
| Pre-8.7 item, first reconcile after upgrade, assignees already agree (or both `None`) | baseline has `"status"` only, no `"assignee"` key; `gh.assignee == jira.assignee` | Zero writes (true no-op) -- both sides already agree, so the first-sync AD-4 comparison finds nothing to decide; the baseline still backfills for free the next time any OTHER field's divergence triggers a write | No error expected |
| Pre-8.7 item, first reconcile after upgrade, assignees already DISAGREE | baseline has `"status"` only, no `"assignee"` key; `gh.assignee != jira.assignee` | **RESOLVED (escalation, finding 1, decision (b)):** treated as a first-sync AD-4 decision for the assignee field alone -- GitHub wins unless `field_overrides["assignee"] == "jira"`; the losing side is written and both baselines record the converged value, exactly as a genuinely new pair would be decided | No error expected; a real, one-time write occurs |
| GitHub `content` unreadable (distinct from a genuine DraftIssue) | e.g. partial GraphQL response, permission gap: `errors` populated or an unexpected shape, not a clean `DraftIssue` | **RESOLVED (escalation, finding 3):** treated as UNKNOWN, not "no assignee" -- assignee decision for this tick downgrades to `no_op` (skip, never write, never clear); does not touch either side's baseline; re-attempted next tick | No error surfaced to the caller for this field alone; item is not failed named unless another field also errors |
| GitHub item carries more than one assignee (an untracked co-assignee exists) | `assignees(first: 10).nodes` has length > 1 | **RESOLVED (escalation, finding 4, decision (a)):** refused named -- no write to either side for this item; the item fails visibly rather than guessing which login is "the tracked one" | `SyncMultipleAssigneesError`, greppable, naming the item and both logins observed |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` --
  - `_VALID_OVERRIDE_FIELDS` (`:93`): extend to `("status", "assignee")`.
  - `_GET_PROJECT_ITEM_QUERY` (`:363-379`): add the `content` fragment described above.
  - `GitHubItemState` (`:450-459`): add `assignee: str | None`, `content_ref: tuple[str, str,
    int] | None` (owner, repo, number).
  - `_parse_field_values` (`:462-484`) area: add a sibling parser for `node["content"]` ->
    `(assignee_login, content_ref)`.
  - `get_project_item` (`:487-516`): wire the new parser into `GitHubItemState`.
  - New: `_github_issue_assignees_url(owner, repo, number)` and `update_github_assignees(owner,
    repo, number, *, add, remove, credential, transport)` -- REST POST/DELETE, mirrors
    `update_jira_issue_fields`'s status-check shape (`< 300` success).
  - `JiraIssueState` (`:646-654`): add `assignee: str | None` (Jira `accountId`).
  - `get_jira_issue` (`:657-693`): add `"assignee"` to `requested_fields`; parse
    `fields.assignee.accountId`.
  - New: `SyncUnmappedUserError(SyncError)` beside `SyncUnmappedStatusError` (`:244-246`).
  - New (escalation, finding 4): `SyncMultipleAssigneesError(SyncError)` -- raised when
    `assignees(first: 10).nodes` has length > 1; names the item and both observed logins.
  - New (escalation, finding 3): `_parse_content` distinguishes a genuine `DraftIssue`/confirmed-
    empty assignee list from an UNREADABLE `content` (populated `errors`, unexpected shape) --
    the latter yields `gh.assignee = UNKNOWN` (a sentinel distinct from `None`), and the
    assignee decision block downgrades to `no_op` whenever it sees `UNKNOWN`, never writing or
    clearing either side.
  - Revised (escalation, findings 1+2): `pair_has_established_baseline`-equivalent logic
    (`sync.py:1183`) becomes per-field, not per-pair -- a missing `"assignee"` key triggers a
    real AD-4 first-sync decision (compare both sides, write the losing side), and a field's own
    persisted write is the only thing that marks THAT field established; another field's
    successful write on the same tick must never do so.
  - `_read_both_sides` (`:809-862`): relax the three trailing hard-fail checks per the Always
    list; return the resolved `(gh, jira)` pair unchanged in shape.
  - `reconcile` (`:865-1075`): generalize the single-field decision block into two structurally
    parallel blocks (status unchanged, assignee new -- duplicate the shape, do not abstract a
    generic engine for two fields); add the link-repair step; extend the merged baseline write
    and `details` dict (new `details["assignee"]`, `details["link_repairs"]` keys; existing
    top-level `decision`/`target_value`/`baseline` keys keep meaning STATUS's own, unchanged, for
    backward compatibility with existing assertions).
  - `load_config` (`:145-223`): add the `user_mapping` string type-check mirroring
    `status_mapping`'s (`:199-209`).
- `.steward/sync-config.example.yaml` -- update the `user_mapping` comment (no longer "reserved
  for a future assignee-sync field"; it is consulted now). No new required keys.
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_config.py` -- add
  `user_mapping` type-safety tests (non-string key/value) mirroring `status_mapping`'s
  (Story 8.6 precedent).
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` --
  extend `FakeTransport`'s `_github` node builder to optionally include a `content` block;
  update `test_neither_changed_is_a_no_op_with_zero_writes` (`:353-371`) to include
  `"assignee": null` in its input baseline fixtures (this pair has already synced once
  post-upgrade); update the 7 tests asserting exact baseline-dict equality (`:209-210, :235-236,
  :270-271, :496-497, :522-523, :562-563, :645-646`) to include `"assignee": None`/its translated
  value; add new tests for each I/O Matrix row above, plus a `--schedule` batch composition test
  for an unmapped-assignee failure (mirrors `test_schedule_batch_with_one_unmapped_status_among_
  linked_items_fails_only_that_entry`) and one for identity-link self-heal composing with
  `--schedule`.

## Tasks & Acceptance

**Execution:**
- [x] `sync.py` -- extend `_VALID_OVERRIDE_FIELDS`, `_GET_PROJECT_ITEM_QUERY`, `GitHubItemState`,
  `JiraIssueState`, `get_project_item`, `get_jira_issue` per the Code Map.
- [x] `sync.py` -- add `SyncUnmappedUserError`, `_github_issue_assignees_url`,
  `update_github_assignees`.
- [x] `sync.py` -- `load_config`: add `user_mapping` string type-check.
- [x] `sync.py` -- `_read_both_sides`: relax the trailing link checks into repair-vs-hardfail
  per the Always list; preserve both existing hard-fail cases exactly.
- [x] `sync.py` -- `reconcile`: add the assignee decision block (mirrors status's shape,
  translated via `user_mapping`/inverse), the link-repair step, the extended no-op fast path,
  the extended `details` dict, and the extended merged baseline write.
- [x] `.steward/sync-config.example.yaml` -- update the `user_mapping` comment.
- [x] `test_sync_config.py` -- add `user_mapping` type-safety tests.
- [x] `test_sync_reconcile_propagation.py` -- extend `FakeTransport`'s GitHub node builder with
  an optional `content` block; fix the one pre-existing no-op test's input fixture and the 7
  baseline-equality assertions; add new tests per the I/O Matrix (assignee push both directions,
  unmapped-assignee failure, explicit-clear bypass, draft-content failure, link self-heal on a
  one-sided-missing pair, link mismatch still hard-fails -- reuse the existing test unchanged --
  the pre-8.7-mismatch-silently-adopted accepted-limitation case, and the two `--schedule`
  composition tests).

**Acceptance Criteria:**
- Given a GitHub item's assignee differs from its Jira counterpart's, when `reconcile` runs,
  then the correct side is written (translated through `user_mapping`) and both baselines record
  the converged value.
- Given a Jira issue's link field is empty but the paired GitHub item's link field already names
  it, when `reconcile` runs, then Jira's link field is written to the GitHub item's ID with no
  human action, and this never touches either side's baseline.
- Given both sides' link fields already hold non-empty, non-matching values, when `reconcile`
  runs, then it still fails named exactly as before -- never silently overwritten.
- Given the full test suite, when `pixi run -e pyforge-steward pyforge-steward-test` runs, then
  it exits 0 including every existing and newly added test, with zero live network calls.

## Review Triage Log

### 2026-08-15 — Review pass

Blind Hunter (`bmad-review-adversarial-general`) and Edge Case Hunter (`bmad-review-edge-case-hunter`)
ran independently, no shared context, against the diff since `baseline_revision`. Every finding
was verified by hand (several via live reproduction against the actual `reconcile()` code) before
triage, not taken at face value from either reviewer's report.

- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 3, medium 1, low 3)
- defer: 3 (low 3)
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` (Blind Hunter) GitHub assignee removal used the stale baseline value as
    the `DELETE` target instead of the live-read `gh.assignee` -- if GitHub's live assignee had
    already drifted from what the baseline recorded, the `DELETE` no-ops against a login that
    isn't actually assigned while the additive `POST` still adds the new person, leaving TWO
    assignees simultaneously and violating this story's own "never manage more than one
    assignee" boundary. Fixed: `update_github_assignees`'s `remove=` now uses `gh.assignee`.
  - `[high]` `[patch]` (Edge Case Hunter) `update_github_assignees` issued DELETE-then-POST; a
    POST failure after a successful DELETE left the GitHub item with ZERO assignees, strictly
    worse than either the old or new state. Fixed: reordered to add (POST) before remove
    (DELETE) -- worst case on partial failure is now briefly two assignees, which self-heals on
    the next reconcile.
  - `[high]` `[patch]` (Blind Hunter, corroborated by Edge Case Hunter's compound-failure
    framing) a later field's `SyncError` (e.g. assignee failing because the linked GitHub item
    is permanently a DraftIssue) aborted `reconcile()` before the single end-of-call merged
    baseline write ran -- stranding an EARLIER field's (status's) already-successful, already-live
    push with a stale baseline forever, causing every subsequent `--schedule` run to re-decide
    status as "changed" and re-push the same transition indefinitely. Fixed: `reconcile()` now
    persists whichever field(s) already succeeded before a later field's failure, via a
    `_persist_merged_baseline()` closure invoked on the failure path too, excluding only the
    field that actually failed.
  - `[medium]` `[patch]` (Edge Case Hunter) the jira:AD-10 "missing baseline key on an established
    pair" backfill check was gated per-SIDE independently rather than per-PAIR, contradicting
    this spec's own Design Notes ("a statement about the PAIR... not about each field in
    isolation"). A reachable asymmetric state (one side's baseline wholly `{}`, e.g. via the
    existing accepted partial-baseline-write-failure precedent, while the other side is
    established but missing just the `assignee` key) let the established, correct side get
    silently overwritten by the empty side's arbitrary current value, with the wrong result then
    permanently adopted as converged. Fixed: the "first-sync AD-4 decision" branch now fires for
    BOTH sides whenever EITHER side's baseline dict is wholly empty.
  - `[low]` `[patch]` (Blind Hunter, corroborated by Edge Case Hunter) `load_config` never
    checked `user_mapping` for duplicate values -- this story is what first makes the computed
    inverse mapping load-bearing (push_to_github translation), so two GitHub logins mapped to
    the same Jira accountId silently collapsed to one in the inverse, with no load-time warning.
    Fixed: `load_config` now raises `SyncConfigError` naming the duplicate.
  - `[low]` `[patch]` (Blind Hunter) `details["assignee"]` never surfaced the actually-persisted/
    translated value, unlike status's `details["baseline"]`. Fixed: added
    `details["assignee"]["written_value"]`.
  - `[low]` `[patch]` (Edge Case Hunter) a link-repair-only round (status/assignee both already
    converged) left `details["baseline"]` at `None` with no distinct signal that a real write
    (to the link field) happened, breaking the pre-8.7 implicit invariant that `baseline is None`
    means zero writes. Verified `details["link_repairs"]` already reflects reality on the success
    path; as a side effect of the partial-persistence fix above, failure paths now also carry a
    populated `details` dict.
  - Six new tests added covering all of the above plus the two coverage gaps the reviewers
    named directly (assignee's own "both diverged to the same translated value" AD-4 tie-break;
    `update_github_assignees`'s non-2xx failure path).

Findings deferred (real, but out of this pass's scope -- see `deferred-work.md`):
- `[low]` `[defer]` `DW-FU-8-7`: the assignee convergence check compares an untranslated GitHub
  login against a Jira accountId, so it can't detect "the destination already converged" and
  triggers a redundant write (visible GitHub DELETE+POST churn) even when both sides already
  agree. Same shape Story 8.6 explicitly accepted for status, but assignee's consequence (live,
  notification-generating churn) differs enough to warrant a dedicated look rather than silently
  inheriting that acceptance.
- `[low]` `[defer]` `DW-FU-8-7-2`: adding `"assignee"` to the shared baseline JSON consumes
  previously-unbudgeted space against Jira's 255-byte field ceiling; the existing
  `SyncBaselineTooLargeError` already handles an overflow named and gracefully, but no test/
  analysis demonstrates realistic margin.
- `[low]` `[defer]` `DW-FU-8-7-3`: tracking only `assignees(first: 10).nodes[0]` assumes an
  ordering GitHub doesn't publicly guarantee; an untracked co-assignee on a real board could
  interfere. Narrows a risk this spec's own Block-If already flagged as unverifiable without
  live API access.

**Re-verification after patches:** `pixi run -e pyforge-steward pyforge-steward-test` -- 716
passed, 0 failed, zero live network calls (710 baseline + 6 new). `pixi run -e pyforge-steward
pyforge-steward-dogfood` -- clean (`steward --version && steward keys audit --drift` succeeds).

### 2026-08-15 — Review pass (follow-up, pass 2)

Blind Hunter (`bmad-review-adversarial-general`) and Edge Case Hunter (`bmad-review-edge-case-hunter`)
ran again in parallel, no shared context, against the same diff since `baseline_revision`. Every
finding below was re-verified by hand against the live code before triage (the two reviewers
converged independently on the first three, which is what promoted the first one's severity).
Each fix was then proven non-vacuous by reverting it in isolation and confirming its new test
fails.

- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 1, medium 2, low 6)
- defer: 4 (low 4)
- reject: 6 (low 6)
- addressed_findings:
  - `[high]` `[patch]` (both reviewers) The assignee convergence check compared the SOURCE side's
    value against the destination's — a GitHub login against a Jira accountId — so under any
    non-identity `user_mapping` it could never match and never fired. That is not the redundant
    write it was taken for in pass 1 (`DW-FU-8-7`): the redundant write is
    `add=<mapped login>, remove=gh.assignee` with BOTH naming the same login whenever the
    destination already agrees, so it POSTs that login and immediately DELETEs it, leaving the
    item with NO assignee — which the next reconcile reads as a genuine unassignment and
    propagates to Jira, converging both systems on "unassigned" permanently and silently. Fixed
    two ways: the convergence check now translates into the destination's own vocabulary before
    comparing (non-raising, so an unmapped value still fails named in the write phase), and
    `update_github_assignees` never issues a DELETE for the login it just added.
  - `[medium]` `[patch]` (both reviewers) `_read_both_sides`' relaxed reciprocity check required
    BOTH sides' links to be non-empty before judging either, so a GitHub item already linked to a
    DIFFERENT Jira issue, paired against a Jira issue whose own link field is empty, was no longer
    refused: the real link was overwritten and status/assignee cross-propagated between two items
    that were never a pair. Pre-8.7 this raised `SyncUnlinkedError`. Fixed: each side's non-empty
    link is judged independently, which preserves the AF-5 empty-side repair exactly while
    restoring the hard fail this spec's own Always list demands ("never silently overwritten").
  - `[medium]` `[patch]` (Blind Hunter) `details["link_repairs"]` was frozen before the write
    phase, so a `SyncError` from status or assignee — which skips the link repairs entirely, they
    are sequenced last — still reported the repair as done. On the literal AF-5 gap with an
    unmapped assignee, the caller was told the link was repaired on every tick while it stayed
    broken. Fixed: the failure path reports repairs actually performed.
  - `[low]` `[patch]` (both reviewers) The baseline-refresh-failure path was the one return that
    omitted `details`, defaulting to `{}` and breaking this function's own stated "read any key
    unconditionally without a KeyError" guarantee on exactly the path where a caller most needs to
    know what did get written; its summary also named status's decision only. Fixed: both.
  - `[low]` `[patch]` (Blind Hunter) `.steward/sync-config.example.yaml` told operators it was
    "safe to leave `user_mapping` empty if you don't want assignee propagated" — false: the first
    genuinely diverging assignee is then a hard failure (and a failed entry in a `--schedule`
    batch). Fixed, and the same comment now documents the two constraints an operator otherwise
    meets as a red run: no duplicate values, and the REST assignee write needs write access to the
    issue's own repository (a Projects-only token is rejected).
  - `[low]` `[patch]` (Edge Case Hunter) `load_config` accepted empty-string `user_mapping` keys
    and values. An empty translated value is falsy, and `update_github_assignees` skips the falsy
    half of its add/remove pair — so the POST was skipped while the DELETE still ran, unassigning
    the item and recording `""` as converged. Fixed: non-empty check at load time.
  - `[low]` `[patch]` (both reviewers) `content["number"]` reached the REST URL as an unvalidated,
    unquoted path segment while `owner`/`repo` were `quote()`-escaped on the same line, against
    this module's own stated "never trust an externally-sourced path segment" precedent. Fixed:
    a `content_ref` is built only for a real `int`.
  - `[low]` `[patch]` (Edge Case Hunter) `_parse_content` assumed every nested container was a
    dict, so a partial or proxied response whose `repository`/`assignees` came back as a list or
    string raised a raw `AttributeError` out of `reconcile` — escaping the module's named-error
    contract and, under `--schedule`, aborting the whole batch instead of one item. Fixed: every
    shape is type-checked and an unusable one reads as the same valid "no assignee" state a
    `DraftIssue` does.
  - `[low]` `[patch]` (both reviewers) Coverage gaps: `field_overrides {assignee: jira}` was
    accepted but no test ever drove that branch; `--dry-run` had no test for the link repair (the
    one write not gated on a "changed" flag); and the fake returned `200 {}` for REST calls without
    applying them, so "assigned the right person" and "POSTed then DELETEd the same login" were
    the same request list — which is why the high finding above was invisible at authoring time.
    Fixed: the fake now applies assignee writes to its own state, and ten tests were added,
    covering every patch above plus those three gaps.

Findings deferred (real, but out of this pass's scope — see `deferred-work.md`; appended as new
entries only, no existing entry modified or re-opened):
- `[low]` `[defer]` `DW-FU-8-7-4`: with both identifiers supplied and NEITHER side carrying a link
  value, reconcile now silently CREATES a reciprocal link between two arbitrary caller-named items
  (pre-8.7 this hard-failed). Unreachable from the shipped CLI, and whether "both named, neither
  linked" should mean "link them" is an intent call, not a mechanical fix.
- `[low]` `[defer]` `DW-FU-8-7-5`: when exactly one side's baseline carries the `"assignee"` key
  and the other's non-empty baseline does not, a live divergence is silently adopted as converged.
  The alternative makes the side with the INCOMPLETE baseline the authority — not self-evidently
  better, so the contract has to be decided first.
- `[low]` `[defer]` `DW-FU-8-7-6`: adding `content` to the shared item-read query couples the
  pre-existing status sync to repository-read permission, because GitHub answers an inaccessible
  node with partial data plus a populated `errors` array and this module treats any `errors` as a
  failure. Confirming that shape needs the live board this spec's own Block-If already defers to.
- `[low]` `[defer]` `DW-FU-8-7-7`: Story 8.1's audit note in the tracked `epics.md` still says
  assignee/link propagation "has no owning story", contradicting the Story 8.7 entry in the same
  file — the exact phrase a decomposition audit greps for, so it invites a duplicate story.

Rejected (6, all low): the single-assignee `assignees[0]` ordering risk and the Jira 255-byte
baseline-ceiling margin are already tracked as `DW-FU-8-7-3` and `DW-FU-8-7-2` — re-filing them
would duplicate entries the orchestrator owns; "duplicate `user_mapping` values should not be a
hard load failure" re-litigates a deliberate pass-1 decision that this story is what makes the
inverse load-bearing (documented now, rather than loosened); Story 8.7's own `Status: backlog`
line in `epics.md` is orchestrator-owned landing bookkeeping on an unmerged branch; the test
helper counting any `repos/` REST call as a write has no consequence today; and the unbounded
link-repair loop requires a Jira field that accepts writes but is absent from the `fields=`
projection, which is speculative configuration.

**Re-verification after patches:** `pixi run -e pyforge-steward pyforge-steward-test` — 726 passed,
0 failed, zero live network calls (716 prior + 10 new). `pixi run -e pyforge-steward
pyforge-steward-dogfood` — clean. Each of the six behavioral fixes was additionally reverted in
isolation and its test confirmed to fail, so none of the new tests is vacuous.

### 2026-08-15 — Review pass (follow-up, pass 3) — INTENT GAP, halted

Blind Hunter (`bmad-review-adversarial-general`) and Edge Case Hunter (`bmad-review-edge-case-hunter`)
ran again in parallel, no shared context, against the same diff since `baseline_revision`. Both
converged independently on the same root cause. Every finding below was reproduced by EXECUTION
against the real `reconcile()` using the suite's own `FakeTransport` (multi-tick, which no existing
test does) before triage -- not taken at face value from either reviewer.

- intent_gap: 4 (high 4)
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

Per the cascading order, the lower categories were NOT triaged this pass -- an intent gap makes
them moot because the code will be re-derived once the contract is resolved. They are listed under
"Carried, untriaged" below so the next pass does not have to re-find them; none was patched,
deferred, or rejected, and `deferred-work.md` was NOT touched this pass.

**The four intent-gap findings** (all four are rooted INSIDE `<intent-contract>`; each needs a
human decision this spec does not contain):

1. `[high]` **The contract forbids the only write that could make assignee propagation work, and
   simultaneously promises it works.** The I/O Matrix's two pre-8.7 rows mandate "Zero writes (true
   no-op)" / "no write, no error, no flag" when the baseline lacks the `"assignee"` key on an
   established pair. The Never section's accepted-limitation bullet promises, of the same state,
   that the value "is silently adopted as the new baseline" and that "Only a LATER change from that
   point forward is detected and propagated normally", and tells the operator that after manually
   aligning both sides once, "ordinary reconcile keeps them converged going forward". These cannot
   both hold: with no write, nothing records that the pair was ever observed, so `sync.py:1183-1191`
   re-derives the adopted baseline from the CURRENT value on every single call and both
   `*_assignee_changed` flags are permanently `False`. **Reproduced:** established pair
   (`{"status": "In Progress"}` both sides, statuses stable), a human assigns `octocat` on GitHub ->
   ticks 1-4 all report `assignee=no_op`, ZERO writes, Jira's assignee stays `None` forever. The
   documented operator workaround does not work either, for the same reason. Net effect: the
   story's headline feature is permanently inert on every pair that predates it -- i.e. every pair
   on any real board -- unless and until an unrelated STATUS change happens to trigger a write.
   Resolving this requires choosing between at least three mutually exclusive options the contract
   does not choose between: (a) accept a one-time backfill write across every already-linked item
   at upgrade (the "write-storm" the contract explicitly rejects), (b) compare the two sides against
   each other when the baseline key is absent and let AD-4 resolve a disagreement (which the
   contract explicitly forbids: "never propagated, never flagged"), or (c) accept that assignee sync
   only ever functions for pairs created after this story (which the contract's own promise denies).

2. `[high]` **A failed assignee write silently and permanently self-heals into "converged".** Same
   root mechanism as (1), reached from the opposite direction. `pair_has_established_baseline`
   (`sync.py:1183`) is computed from baseline truthiness, and a first-link round whose STATUS
   diverged still persists `{"status": ...}` to both sides even when the assignee write failed
   (`_persist_merged_baseline`, `sync.py:1566-1573`, correctly excludes only the failed field).
   That write is what MAKES the pair "established" -- so from the next tick the missing-key adoption
   branch fires and the failure disappears. **Reproduced:** first link, GitHub assigned to `ghost`
   (no `user_mapping` entry). Tick 1 fails loud and correctly (`unmapped: github login 'ghost'...`);
   ticks 2 and 3 report `no_op`, `ok=True`, zero writes, board green -- end state GitHub `ghost`,
   Jira `None`, forever. This directly falsifies the code's own comment at `sync.py:1556-1563`
   ("it is correctly re-attempted on the next reconcile"). Reachable from ANY first-link assignee
   write failure: unmapped user, `content_ref is None`, GitHub 4xx, transport error.

3. `[high]` **The contract defines an unreadable GitHub `content` as an authoritative
   unassignment, which silently destroys a real Jira assignee.** The Always list mandates that a
   `content` which is a `DraftIssue` "(or absent, e.g. every pre-8.7 test fixture) reads as
   `gh.assignee = None`, `content_ref = None` -- valid 'no assignee' state, never an error", and
   `_parse_content` (`sync.py:591-616`) implements exactly that. But "absent" conflates two states
   the contract never distinguishes: "this is a DraftIssue, it genuinely has no assignee" and "this
   read could not see the issue, the value is UNKNOWN". **Reproduced:** a converged pair on
   `octocat`/`acc_octocat` with both baselines recording it; one read returns `content` without a
   readable `assignees` block -> `push_to_jira target_value=None` -> **Jira's assignee is cleared**,
   both baselines rewritten to `assignee: null`, `ok=True`, and the loss is now "converged" and
   never self-heals when the read recovers. This is not hypothetical for this story: the
   `.steward/sync-config.example.yaml` comment added by this very diff anticipates an operator
   running a Projects-only token, which is precisely a token that cannot read a private repo's
   issue `content`. Whether an unreadable content should be treated as an unassignment, an error,
   or an "unknown -> no_op" is an intent call, and the contract has already made it the dangerous
   way without weighing this consequence.

4. `[high]` **The contract's "track only `assignees[0]`" read rule and its "never manage more than
   one GitHub assignee" invariant contradict each other whenever a co-assignee exists.** The Always
   list mandates tracking only the first of `assignees(first: 10)`; the Never list forbids ever
   leaving more than one assignee. **Reproduced:** GitHub issue carries `[octocat, hubot]` (`hubot`
   added by hand, never known to this module), baselines record `octocat`/`acc_octocat`, and a human
   reassigns Jira to `alice`. Tick 1 -> `add=alice, remove=octocat` -> GitHub is `['hubot',
   'alice']`, **two assignees, violating the invariant**. Tick 2 -> `gh.assignee` now reads `hubot`
   != baseline -> `push_to_jira hubot` -> **Jira is silently reverted from `alice` to `acc_hubot`**,
   `ok=True`, no diagnostic. Tick 3 no-ops, permanently settled on the wrong person. `DW-FU-8-7-3`
   tracks the `assignees[0]` ORDERING risk but not this revert-and-corrupt outcome, which needs no
   ordering ambiguity at all. Resolving it means deciding what a co-assigned item MEANS (refuse it
   named, manage only this module's own tracked login, or keep current behavior) -- not a mechanical
   fix.

**Why the two prior passes did not catch these.** Both are single-tick blind spots that the diff's
own test design cannot see: every one of the ~14 assignee fixtures has exactly ONE `assignees.nodes`
entry, and every assignee test calls `reconcile()` exactly ONCE -- while the module's central claim
(the zero-loop property) is a MULTI-tick property that Story 8.2 proved for status with N round
trips. `test_pre_8_7_pair_assignees_already_disagree_is_silently_adopted_not_resolved` enshrines the
intended one-tick behavior and is structurally incapable of observing that it never advances.

**Carried, untriaged this pass** (real, reproduced or code-confirmed, but moot under the cascading
order -- re-triage after the contract is resolved; NOT added to `deferred-work.md`, and no existing
ledger entry was modified, re-opened, or rewritten):
- `[medium]` A `SyncError` from STATUS permanently blocks assignee AND the stateless link repair for
  that pair (fixed write order in one `try`, `sync.py:1399-1523`); status's own failure recurs every
  tick, so the link never repairs. The `*_persist_ok` design addressed the converse direction only.
- `[medium]` Two GitHub items whose `gh_link` both name one Jira issue whose own link is empty: the
  relaxed per-side check (`sync.py:1091`) lets whichever is dispatched first permanently marry it,
  and the real pair then fails "not a reciprocal pair" every tick.
- `[medium]` The STATUS convergence check compares source vocabulary against destination vocabulary
  -- the exact bug pass 2 fixed for assignee -- and the new comment at `sync.py:1279-1281` asserts
  status does not have it. Pre-existing (Story 8.6 accepted it), but now newly load-bearing.
- `[low]` `_read_both_sides`' failure return (`sync.py:1138`) omits `details`, breaking the "read
  any key unconditionally without a KeyError" guarantee that pass 2 fixed on the sibling path.
  Reproduced: `details == {}`, `details["link_repairs"]` raises `KeyError`.
- `[low]` `details["baseline"]` reports only status and is set even when status was a `no_op`;
  assignee's persisted baseline value is never reported.
- `[low]` `target_value`/`assignee_target_value` survive the downgrade to `no_op` and are reported
  as if targeted -- read by `--dry-run`, the operator preview.
- `[low]` `update_github_assignees` does not verify the POST actually landed (GitHub silently drops
  a non-collaborator), so the baseline can record a write that never happened.
- `[low]` GitHub logins are case-insensitive but `remove != add` is compared case-sensitively, so a
  `user_mapping` whose casing differs from GitHub's canonical login POSTs then DELETEs the same user.
- `[low]` `.steward/sync-config.example.yaml` now documents a hard failure that findings (1) and (2)
  show does not actually occur for pre-existing pairs.
- `[low]` The Jira unassign body `{"assignee": null}` is unverified against Jira Cloud, which
  documents `{"assignee": {"accountId": null}}`; every test of it goes through the fake.

Rejected as duplicates of ledger entries the orchestrator already owns: the "both identifiers, neither
linked -> force-marry" case (`DW-FU-8-7-4`), the GraphQL partial-data/`errors` permission coupling
(`DW-FU-8-7-6`), and the `assignees[0]` ordering risk itself (`DW-FU-8-7-3`).

**Deviation from the workflow's intent_gap branch, recorded deliberately.** The branch instructs
"Revert code changes". That was NOT done. This repo carries a standing, fleet-wide,
user-set escalation policy -- preserve then restore-patch, never re-implement from scratch -- and
discarding ~1,800 lines carrying two prior review passes' verified fixes ahead of a human
intent decision is exactly what that policy exists to prevent. The branch is left intact at
`6d5d748d48` and additionally preserved at
`attempt-preserve/8-7-assignee-and-identity-link-propagation-intentgap`. Nothing in the four
findings above invalidates the diff wholesale: three of them are resolved by amending the contract
and re-deriving the affected decision block, not by starting over.

**Verification performed this pass:** `pixi run -e pyforge-steward pyforge-steward-test` -- 726
passed, 0 failed (unchanged from pass 2; the suite is green and does not observe any of the four
findings). Four separate multi-tick reproduction harnesses were run against the real `reconcile()`
via the suite's own `FakeTransport`; all four findings reproduced exactly as described. No source
file was modified this pass.

### 2026-08-15 — Escalation resolved (human decision)

Walked through all four intent-gap findings interactively with the operator. Decisions:

1. **Finding 1 (root cause):** option (b) -- a missing `"assignee"` baseline key is a first-sync
   AD-4 decision for that field alone (compare both sides, write the losing side), the same
   mechanism status already uses. Rejected (a) one-time backfill write-storm and (c) restricting
   assignee sync to post-story pairs only.
2. **Finding 2:** agreed as originally proposed -- "established" tracked per field, not derived
   from the pair's overall baseline truthiness.
3. **Finding 3:** agreed as proposed -- an unreadable `content` is UNKNOWN, downgrades to
   `no_op`; only a genuine `DraftIssue`/confirmed-empty list is "no assignee."
4. **Finding 4:** option (a) -- a GitHub item carrying more than one assignee is refused named
   (`SyncMultipleAssigneesError`), never silently tracked via `assignees[0]`.

Intent contract (Always/Never/I-O Matrix), Code Map, and Design Notes amended to encode all four
decisions unambiguously. Work preserved at `attempt-preserve/8-7-assignee-and-identity-link-
propagation-intentgap` (`6d5d748d48`) is NOT discarded -- re-derivation re-drives from that diff
via a restore-patch, not from scratch, per this repo's standing preserve-then-restore-patch
policy. `deferred-work.md` untouched (nothing newly deferred by this resolution; the "carried,
untriaged" findings from pass 3 remain for the next review pass to triage against the corrected
contract).

## Design Notes

**Why assignee and identity-link use different mechanisms.** Status/assignee are genuinely
mutable, symmetric business values -- either side can independently change them, and a real
simultaneous conflict is possible (AD-4 decides). The identity link is structurally different:
GitHub's link field holds Jira's key, Jira's link field holds GitHub's ID -- not mirrored copies
of one shared value, so there is no "whichever side changed, propagate it" question, and no
conflict is possible (both sides' correct values are always simultaneously and independently
knowable from the resolved pair itself). Forcing it through the single-tracked-field decision
enum (`push_to_jira` XOR `push_to_github` XOR `no_op`) produces a real bug: if only one side
needs repair, the arbitrary tie-break can choose the direction that turns out to already match,
downgrade to `no_op` via the convergence check, and leave the genuinely broken side untouched
forever. A stateless, unconditional, independent-per-side repair has no such failure mode.

**Why a missing baseline key IS a first-sync decision, per field (revised 2026-08-15, escalation
findings 1+2).** jira:AD-10 rule 1 ("absent baseline is a first link") was written when status was the
only tracked field, so "baseline is `{}`" and "the status key is absent" were identical
conditions. Adding assignee exposes the case they never had to distinguish: a pair with an
ESTABLISHED history for `status` but no `assignee` key. The prior design read jira:AD-10 rule 1 as a
statement about the PAIR ("has this pair ever converged") and silently adopted a missing-key
field's current value without comparing sides -- reproduced live as a permanent dead feature
(finding 1) and a silent-failure-heals-itself bug (finding 2). jira:AD-10 rule 1 is instead read PER
FIELD: a missing `"assignee"` key -- whether the pair's baseline is wholly empty or just missing
that one key -- is a first-sync AD-4 decision for assignee alone, exactly parallel to how a
wholly-new pair is decided today. If the two sides already agree, AD-4's comparison finds nothing
to change and no write happens (indistinguishable from a no-op). If they disagree, AD-4 resolves
it exactly as a real conflict (GitHub wins unless overridden) and writes the losing side --
**this is a real, one-time write per genuinely-mismatched pre-existing pair**, not the
recurring write-storm the prior design avoided (each pair converges once, then behaves like any
other established pair from then on). "Established," for the purpose of deciding whether a
field's own key is present, is now tracked strictly per field (finding 2) -- a status write
succeeding on a tick where the assignee write fails must never backfill the assignee key, or the
failure would masquerade as "already observed" on the very next tick. A genuinely new pair (`{}`
on both sides, per Story 8.1's existing `test_first_link_no_baseline...` tests) is unaffected --
AD-4 still decides a real first-link conflict exactly as today; this revision only extends the
SAME mechanism to the missing-single-field case instead of special-casing it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done
Reconciled 2026-09-20: the `blocked` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `72c86bd002 2026-08-15 steward: promote story 8.7 to done in the tracked ledger` — that promotion is the ruling this record now reflects.
Blocking condition: intent gap in intent contract

**What ran.** A follow-up review pass (pass 3) on the `done` spec, per `bmad-dev-auto` step-01's
`done` -> fresh-review route. No implementation work; no source file was modified this pass.

**Outcome.** Four `intent_gap` findings, all rooted inside `<intent-contract>`, all reproduced by
execution against the real `reconcile()` (multi-tick, which no existing test does). Full detail in
`## Review Triage Log`, entry "2026-08-15 — Review pass (follow-up, pass 3)". In one line each:

1. The I/O Matrix forbids the backfill write ("Zero writes") on a pre-8.7 pair while the Never
   section promises later assignee changes are "detected and propagated normally" — mutually
   exclusive, and the consequence is that assignee propagation is permanently inert on every pair
   that predates this story.
2. Any first-link assignee write failure is silently converted into "converged" from the next tick
   onward, because status's own successful baseline write is what makes the pair "established".
3. The contract defines an unreadable GitHub `content` as an authoritative unassignment, which
   silently and permanently destroys a real Jira assignee — reachable with the Projects-only token
   this diff's own config comment anticipates.
4. "Track only `assignees[0]`" and "never manage more than one GitHub assignee" contradict each
   other whenever a co-assignee exists: the result is two GitHub assignees, then a silent revert of
   a human's Jira reassignment.

**Decision required from a human** (this is what blocks): for finding 1, choose between accepting a
one-time upgrade backfill write across already-linked items, resolving a missing-baseline assignee
divergence via AD-4, or explicitly scoping assignee sync to pairs created after this story. Findings
2 and 3 follow from that choice plus one further call each (should a failed field write be
prevented from being masked by another field's baseline write; should an unreadable `content` be
`unknown -> no_op` rather than an unassignment). Finding 4 needs a decision on what a co-assigned
GitHub item means.

**Verification performed.** `pixi run -e pyforge-steward pyforge-steward-test` — 726 passed, 0
failed, zero live network calls (unchanged from pass 2; the green suite does not observe any of the
four findings). Four multi-tick reproduction harnesses run against the real `reconcile()` via the
suite's own `FakeTransport`; all four findings reproduced exactly as described.

**Work preservation (deviation from the workflow's intent_gap branch, deliberate).** The branch
instructs "Revert code changes"; that was not done, per this repo's standing fleet-wide
preserve-then-restore-patch escalation policy. The branch is intact at `6d5d748d48` and additionally
preserved at `attempt-preserve/8-7-assignee-and-identity-link-propagation-intentgap`. Three of the
four findings are resolved by amending the contract and re-deriving the affected decision block, not
by starting over.

**Ledger.** `deferred-work.md` was NOT touched this pass — under the cascading order an intent gap
makes `defer` findings moot, so this pass deferred nothing. No existing ledger entry was modified,
re-opened, or rewritten. Ten further real findings are recorded under "Carried, untriaged this pass"
in the triage-log entry so the next pass need not re-find them.

**Residual risks.** The branch is green and looks shippable — 726 passing tests, two prior review
passes — while assignee propagation does not function on any pre-existing pair and two silent
data-loss paths are live. Landing it as-is would ship a feature that is inert in production and a
regression risk to Jira assignee data. The four findings are contract-level, not code-level: a
re-run of this same review against the same contract will reach the same halt.

## Status reconcile 2026-09-20

- Auto Run Result `Status: blocked` → `done` (see the reconcile line under it).
