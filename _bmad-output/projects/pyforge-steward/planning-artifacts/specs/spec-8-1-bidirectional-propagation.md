---
title: 'Bidirectional propagation (Epic 8 Story 8.1, pyforge-steward)'
type: 'feature'
created: '2026-08-09'
status: done
baseline_revision: 'c41ed99363048db22f6d0b3ea835f6342031ba48'  # this run's actual starting HEAD; see Auto Run Result for why the prior value was stale
final_revision: '518e3747d226c9b2920f50f070338ff875e31e5f'
review_loop_iteration: 0  # reset — contract re-issued 2026-08-10, this is a fresh build
followup_review_recommended: false
context:
  - '{project-root}_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-jira-github-projects-sync/SPEC.md'
  - '{project-root}/docs/intake/jira-github-projects-sync/jira-github-projects-sync-prd-and-architecture.md'
warnings: ['oversized', 'contract-reissued-2026-08-10']
---

<intent-contract>

> **RE-ISSUED 2026-08-10 from AD-5's third amendment (PR #390).** The previous contract named a
> mechanism that is structurally unimplementable: it compared each side's `updated_at` against a
> sync point stored as a field **on that same item**, so the bookkeeping write advanced the very
> value it was being compared against. Three of this story's own review passes established that by
> trace, and it correctly HALTed rather than repair a frozen contract it could not amend. The
> mechanism below is the replacement. **Do not reintroduce a timestamp comparison anywhere on the
> correctness path.**

## Intent

**Problem:** Two boards, one truth is unimplemented — nothing in this repo talks to Jira or
GitHub Projects V2, so a status/assignee/identity-link change on an external GitHub Projects V2
item or its linked Jira Cloud issue never reaches the other side without a human retyping it.

**Approach:** Add a fifth Steward duty, `sync`, whose `reconcile` verb re-reads both linked
items' current state (never trusts a webhook payload as the change itself), asks of each side
**"does its current value differ from the baseline it was last synced to?"** (AD-5, with the
baseline's shape and lifecycle fixed by jira:AD-10), and converges the divergent side — a GitHub
GraphQL client and a Jira REST client built on the existing `_http.py`/`keys.py` auth delegate,
wired to a **`on: schedule`** GitHub Actions workflow template by default (zero
infrastructure), with an OPT-IN near-real-time path in BOTH directions via
`repository_dispatch` — Jira→GitHub from a Jira Automation, GitHub→Jira from an external
receiver (a GitHub App with org-level Projects read access, or a webhook endpoint) that
consumes the `projects_v2_item` webhook. CORRECTED 2026-08-09: there is no
`project_v2_item` `on:` trigger; see AD-1.

**The change signal is a value, never a clock.** Neither side differs from its baseline → no-op.
Exactly one differs → propagate it. Both differ → a genuine conflict, resolved by AD-4. This is a
three-way merge against a shared base, and it is what makes a simultaneous conflicting edit
detectable at all.

## Boundaries & Constraints

**Always:**
- Every outbound request's auth goes through `keys.HostScopedCredential`/`resolve_headers` →
  `_http.py`'s `auth_headers_for` — never build new credential/header logic (AD-2/AD-8, mirrors
  `keys.py`'s own delegate pattern exactly).
- Control-plane state (the entity link and the per-field **baseline**) lives only as configured
  fields on the items themselves — no sidecar store of any kind (AD-2, jira:AD-10).
- The baseline is a **per-field map of last-synced values, per side** (jira:AD-10), not a timestamp.
  Three lifecycle rules are fixed by jira:AD-10 and are not this story's to re-decide:
  - an **absent baseline is a first link**, not a loop candidate — reconcile it, and if both
    sides already hold differing values AD-4 decides;
  - a **missing key and a null value mean opposite things** — "field cleared on this side" is an
    explicit null sentinel, "field never synced" is the key's absence;
  - **exceeding the vendor's field-size ceiling is AD-2's escape hatch to Mode B**, never a
    licence to invent a sidecar store. Re-verify the real ceiling against the live API rather
    than assuming a limit.
- On a real conflict (both sides diverge from the baseline), GitHub's value wins unless the field
  carries an explicit override in `SyncConfig.field_overrides` (AD-4) — the resolution is a pure
  function of (github_value, jira_value, field_mapping), never a cross-vendor wall-clock
  comparison.
- The webhook/dispatch payload is only ever a wake-up naming which item to look at — every
  `reconcile` call re-reads both sides' current state before deciding anything (AD-9, the
  event-triggered-reconciliation paradigm).
- `sync.py` is a `Duty`-protocol adapter exactly like `keys.py`/`deploy.py`/`provision.py`/
  `budget.py`: never calls `sys.exit()`, always returns `DutyResult` (AD-8 — pinned by
  `tests/meta/test_invariants.py::test_no_duty_module_calls_sys_exit` and
  `tests/conformance/test_duty_protocol.py::test_every_declared_duty_resolves_to_a_conforming_implementation`,
  both of which walk `DUTIES`/`steward/*.py` generically and need no edits for this story).
- Every GitHub/Jira HTTP call goes through an injectable `transport` callable (default a real
  `urlopen`-backed one built on `_http.py`'s `open_url`) so tests never make a live network call
  and need no new mocking dependency.
- No new runtime dependency beyond stdlib + the already-declared PyYAML; argparse only —
  `tests/meta/test_invariants.py::test_no_cli_framework_dependency` forbids click/typer.

**Block If:** none. Q2/Q3/Q4 are resolved (AD-1 through jira:AD-10, architecture `status: final`,
amended 2026-08-10). This run's environment has no live external GitHub Projects V2 board, no
live Jira Cloud project, and no credentials for either — expected for an unattended build of a
greenfield external-system integration, not an intent gap. It is handled below as an
operator-executed manual verification step, not a mid-build decision to halt on.

**Never:**
- **Never branch a correctness decision on a timestamp** (AD-5). `updated_at` has exactly one
  permitted use: under `trigger=schedule`, selecting *which items to look at* so a large board
  need not read every baseline. That filter must be deliberately **over-inclusive** — a false
  positive costs one wasted read and converges to a no-op, a false negative silently drops a
  change. A timestamp MAY be recorded alongside the baseline for operator telemetry ("last
  converged at"); nothing may branch on it.
- Never store a marker inside the object it is used to observe. That is the exact defect this
  contract was re-issued to remove: writing a sync-point field onto an item advances that item's
  own aggregate `updated_at`, so no tolerance value can distinguish the engine's own bookkeeping
  write from a coincidental genuine edit.
- Never touch `.claude/skills/conda-forge-expert/scripts/_http.py`. Jira Cloud auth resolves
  through its existing generic `.netrc` fallback (Basic auth: email as login, API token as
  password); GitHub auth through its existing `GITHUB_TOKEN`/`GH_TOKEN` branch. No new branch
  added there, and this story does not read or modify anything else under
  `.claude/skills/conda-forge-expert/`.
- Never write to this repo's own `sprint-status-ledger.yaml`, dashboard feed, or any build-line
  artifact (Q1/Non-goals) — the target board/project is external and named only in
  `SyncConfig`.
- Never implement Mode B (`dlt`/PostgreSQL) — opt-in, out of scope for this story (AD-7).
- Never auto-provision the GitHub/Jira custom fields this story reads/writes (the identity-link
  field on each side, the baseline field on each side). Their existence and field IDs are an
  operator-supplied `SyncConfig` precondition, not something this story creates via API.
- Never claim a formally proven zero-loop or idempotency guarantee. AD-5's value-comparison guard
  and the reconcile-not-propagate paradigm are implemented and exercised by this story's own
  basic-case tests, but the N-round-trip zero-loop proof (CAP-2) and identical-payload-twice
  idempotency proof (CAP-3) are Story 8.2 / Story 8.3's dedicated acceptance tests — do not
  write those tests here, and do not claim either guarantee is "proven" in this story's summary.
- Never build a general status-vocabulary translation table. This story propagates the
  configured field's raw value 1:1; if the target API rejects it (e.g. Jira has no transition
  matching the pushed status name), that rejection surfaces as a duty-level failure — never
  silently swallowed or reported as success. The reviewable translation table + explicit
  hard-fail-on-unmapped is Story 8.5.

## I/O & Edge-Case Matrix

`base` = the value recorded in that side's baseline map for the field under reconciliation.

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| GH changed, Jira didn't | `gh.value != gh.base`, `jira.value == jira.base` | Jira issue updated/transitioned to match GH's value; both sides' baselines rewritten to the converged value | No error expected |
| Jira changed, GH didn't | inverse of above | GH item field updated via `updateProjectV2ItemFieldValue`; both baselines rewritten | No error expected |
| Both changed (real conflict) | `gh.value != gh.base` and `jira.value != jira.base`, and the two values differ | GitHub's value wins per AD-4 (unless `field_overrides` says otherwise); Jira updated to match; both baselines rewritten | No error expected — deterministic, not an exception |
| Both changed to the SAME value | both differ from base, values now equal | Converged already: no write to either API; both baselines rewritten to that value | No error expected — not a conflict |
| Neither changed (loop candidate / redelivery / echo) | `gh.value == gh.base` and `jira.value == jira.base` | No write to either API; `reconcile` reports a no-op decision. **This is the zero-loop property**, and it holds regardless of when the reconcile runs | No error expected |
| First link (no baseline yet) | the item's baseline field is absent, or has no key for this field | Not a loop candidate. Reconcile as a first sync; if both sides already hold differing values, AD-4 decides. Baselines written afterward | No error expected |
| Field cleared on one side | `gh.base` holds a value, `gh.value` is the explicit null sentinel | Treated as a genuine change to "empty" and propagated — never confused with "never synced", which is the key's absence | No error expected |
| `--dry-run` on any of the above | same as above + `dry_run=True` | Same decision computed and reported; zero write calls made | No error expected |
| Link unresolvable | the item passed on the CLI has an empty/missing identity-link field value | `reconcile` returns `ok=False` naming the unlinked item; no write attempted | Named, logged failure — never crashes, never a silent skip |
| Baseline exceeds the vendor field-size ceiling | the serialized baseline map will not fit the configured field | Named, logged failure pointing at Mode B (AD-2/jira:AD-10) — never falls back to a sidecar store | Named, logged failure |
| Target API rejects the pushed value | e.g. Jira has no transition matching the GitHub status string | The API call's error propagates as a duty-level failure | Named, logged failure — never swallowed or reported as success |

</intent-contract>

## Code Map

**Ground truth as of this session (verified, not assumed):** `sync.py`, `cli.py`'s wiring, the
example config, the workflow-template docs, and all four test files already exist on this
branch, landed for real via PR #383 (`land/steward-8-1`) — but PR #383 landed a *pre-fix*
snapshot (byte-identical to review-pass-3's `4953d427...`) that still carries the confirmed-
broken timestamp loop guard (PR #389 corrected the sprint-status ledger from `done` back to
`backlog` for exactly this reason). Nothing here is a fresh scaffold; every item below is a
targeted MODIFY of already-landed code, replacing the timestamp mechanism with the amended
AD-5/jira:AD-10 per-field baseline-value mechanism. No cherry-pick is needed or performed.

- `src/pyforge/steward/sync.py` -- MODIFY (already landed, 874 lines). Replace the timestamp
  loop guard (`updated_at` vs. a `sync_point` field) with the jira:AD-10 per-field baseline map:
  rename `SyncConfig`'s `*_sync_point_field_id` → `*_baseline_field_id`; replace
  `GitHubItemState`/`JiraIssueState`'s `updated_at: datetime` / `sync_point: datetime | None`
  with `baseline: dict[str, object]`; drop `_parse_timestamp` and the now-unused
  `datetime`/`timezone` imports and GraphQL/REST timestamp fields; rewrite `reconcile`'s
  decision logic and post-write refresh to compare and record values, never timestamps; add
  `SyncBaselineTooLargeError` + the field-size-ceiling check (AD-2/jira:AD-10's escape hatch to
  Mode B). See Design Notes for the full algorithm.
- `src/pyforge/steward/cli.py` -- unchanged. Already wires `sync` as the fifth duty; nothing
  here is mechanism-specific.
- `src/pyforge/steward/keys.py` -- read-only reuse: `HostScopedCredential`, `resolve_headers`.
  Unchanged.
- `.claude/skills/conda-forge-expert/scripts/_http.py` -- read-only reuse via `keys.py`'s
  existing bridge (`locate_http_module`); not modified.
- `.steward/sync-config.example.yaml` -- MODIFY (already landed). Rename both
  `sync_point_field_id` keys to `baseline_field_id`; rewrite their comments to describe the
  jira:AD-10 per-field baseline map, not a sync-point timestamp.
- `.gitignore` -- unchanged (already ignores the operator's real `.steward/sync-config.yaml`).
- `docs/reference/sync-jira-github-workflow-templates/README.md` -- MODIFY (already landed).
  Update the two field-provisioning bullets and the manual-verification step's language from
  "last-sync-point timestamp"/"sync-point fields advance" to the baseline map.
- `docs/reference/sync-jira-github-workflow-templates/*.yml.template` -- unchanged; neither
  template references the sync-point/baseline field by name.
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` --
  REWRITE (already landed, 20 tests). New `FakeTransport` fixture and every case rebuilt for
  baseline-map comparison; add cases for I/O Matrix rows the old suite never covered: first
  link (no baseline yet), field cleared via an explicit null sentinel vs. never-synced (absent
  key), both sides changed to the identical value, and the baseline-exceeds-ceiling failure.
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_config.py` -- MODIFY
  (already landed). Rename fixture/assertion field names to `baseline_field_id`.
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_duty.py` -- MODIFY (already
  landed). Rename fixture field names; drop `updatedAt`/`updated` from the fake transport
  payloads.
- `src/shared/packages/pyforge-steward/tests/unit/test_cli.py` -- unchanged; no sync-point
  references here.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/steward/sync.py` -- rename `SyncConfig.github_sync_point_field_id` /
  `jira_sync_point_field_id` to `github_baseline_field_id` / `jira_baseline_field_id` (update
  `_REQUIRED_GITHUB_FIELDS`/`_REQUIRED_JIRA_FIELDS`, `load_config`'s construction call) -- the
  config surface now names a baseline field, not a timestamp field.
- [x] `src/pyforge/steward/sync.py` -- replace `GitHubItemState`/`JiraIssueState`'s
  `updated_at`/`sync_point` with `baseline: dict[str, object]`; add `_parse_baseline(raw, *,
  side, identifier)` (absent/empty → `{}`; malformed JSON or non-dict → `SyncAPIError`) -- the
  jira:AD-10 per-field baseline map read.
- [x] `src/pyforge/steward/sync.py` -- drop `updatedAt` from `_GET_PROJECT_ITEM_QUERY` and
  `"updated"` from Jira's requested fields (unused once nothing compares against a timestamp);
  remove `_parse_timestamp` and the `datetime`/`timezone` imports.
- [x] `src/pyforge/steward/sync.py` -- `get_project_item`/`get_jira_issue` read the baseline
  field via `config.github_baseline_field_id`/`config.jira_baseline_field_id` and populate
  `.baseline` via `_parse_baseline`.
- [x] `src/pyforge/steward/sync.py` -- rewrite `reconcile`'s loop guard: `gh_changed`/
  `jira_changed` = the side's current tracked-field ("status") value differs from its own
  baseline map entry for that field, where an absent key (`dict.get(field, _MISSING)`) counts
  as changed (jira:AD-10 rule 1, first link — never collapsed with an explicit `None`, jira:AD-10 rule
  2). Neither changed → no-op, no writes. Exactly one changed → propagate it. Both changed →
  AD-4 conflict authority.
- [x] `src/pyforge/steward/sync.py` -- keep the value-equality convergence check downstream of
  the loop guard (now: "the computed target already equals the destination's current value") --
  still required for the "both sides independently changed to the identical value" row; narrower
  purpose than the item-level-staleness workaround it replaces, since the new per-field
  comparison no longer has that failure mode.
- [x] `src/pyforge/steward/sync.py` -- after `dry_run`/true-no-op are excluded, always refresh
  BOTH sides' baseline map (merging the new `"status"` value into any existing map, never
  overwriting a key this story doesn't track) via new `_serialize_baseline(baseline, *, side,
  ceiling)`; add `SyncBaselineTooLargeError` and `_GITHUB_BASELINE_FIELD_CEILING` (1024,
  documented as an unverified conservative placeholder — no public GitHub Projects V2 text-field
  limit was found) / `_JIRA_BASELINE_FIELD_CEILING` (255, Jira Cloud's documented
  "Text Field (single line)" database-level cap) enforcing AD-2/jira:AD-10's escape hatch to Mode B.
- [x] `src/pyforge/steward/sync.py` -- update the module docstring for the AD-5(amended)/jira:AD-10
  mechanism; remove the two now-obsolete "Design Notes correction" callouts (timestamp captured
  after the write; item-level vs. field-level staleness) that described the retired mechanism.
- [x] `.steward/sync-config.example.yaml` -- rename both `sync_point_field_id` keys to
  `baseline_field_id`; rewrite their comments for the jira:AD-10 baseline map.
- [x] `docs/reference/sync-jira-github-workflow-templates/README.md` -- update the two
  field-provisioning bullets and the manual-verification step's language accordingly.
- [x] `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py`
  -- rewrite the `FakeTransport` fixture and every case for baseline-map comparison; add the
  four new cases named above.
- [x] `src/shared/packages/pyforge-steward/tests/conformance/test_sync_config.py` -- rename
  fixture/assertion field names to `baseline_field_id`.
- [x] `src/shared/packages/pyforge-steward/tests/conformance/test_sync_duty.py` -- rename
  fixture field names; drop `updatedAt`/`updated` from the fake transport payloads.

**Acceptance Criteria:**
- Given a linked pair with no recorded baseline on either side (first link) and differing
  status values, when `steward sync reconcile` runs, then AD-4 authority (GitHub wins by
  default) decides and both sides' baseline fields are written afterward.
- Given a linked pair where GitHub's status differs from its own baseline and Jira's does not,
  when `reconcile` runs, then Jira is updated to match and both sides' baseline fields are
  refreshed to the converged value.
- Given the same setup with `--dry-run`, when `reconcile` runs, then no write call reaches
  either API and the reported decision matches what a non-dry-run call would have made.
- Given both sides independently changed to the identical new value, when `reconcile` runs,
  then no API write happens but both baseline fields are still refreshed to that value —
  closing the loop for every subsequent reconcile of that pair.
- Given a serialized baseline map that would exceed the configured field's size ceiling, when
  `reconcile` attempts to write it, then it returns a named, logged failure pointing at Mode B
  — never a sidecar store.
- Given `sync` is already in `DUTIES`, when
  `tests/conformance/test_duty_protocol.py::test_every_declared_duty_resolves_to_a_conforming_implementation`
  runs, then it passes unmodified (structural proof the duty still conforms).
- Given the full suite, when `pixi run -e pyforge-steward pyforge-steward-test` runs, then it
  exits 0 with zero live network calls made by any `sync` test.

## Spec Change Log

### 2026-08-09 — Review pass 1 (bad_spec)

**Triggering findings:**
1. (Blind Hunter, HIGH) The reconcile algorithm as originally specified said the sync-point
   must be written "not older than the write's own timestamp" but did not say HOW to obtain such
   a value — the implementation captured `datetime.now()` once, before any write, which can
   never be guaranteed >= a subsequent write's server-side `updatedAt`. Result: after any real
   push, the item's `updated_at` reads as newer than its own just-recorded sync point forever,
   permanently defeating the AD-5 loop guard for that item.
2. (Blind Hunter + Edge Case Hunter independently) The algorithm never compared the computed
   target value against the destination's current value before deciding to push. Combined with
   AD-5's item-level (not field-level) staleness check, ANY unrelated field edit on either side
   (assignee, an untracked custom field) would drive a live push/transition attempt for a value
   the destination already holds — and since many Jira workflows have no self-transition, this
   commonly hard-fails with `SyncAPIError` on completely benign, unrelated edits.

**What was amended:** the "Reconcile algorithm" block under Design Notes — added the
value-equality short-circuit (point 1) and moved/clarified the sync-point timestamp capture to
strictly after the cross-system write completes, with the rationale for why exact
server-timestamp equality isn't required once the value-equality check exists as a backstop
(point 2). No change to Intent, Boundaries & Constraints, or the I/O & Edge-Case Matrix — all
three remain accurate; this was an algorithm-precision gap, not a boundary or scenario gap.

**Known-bad state avoided:** a story whose own headline capability (bidirectional propagation)
silently defeats its own loop guard on first use, and separately hard-fails on routine,
unrelated board activity — both would surface as confusing, hard-to-diagnose operator-facing
failures well after this story is marked done.

**KEEP instructions (re-derive faithfully, do not redesign):**
- Overall module shape: one file (`sync.py`) mirroring `keys.py`/`deploy.py`'s "one module per
  duty" precedent — `SyncConfig`/`SyncConfigError`/`load_config`, the GitHub GraphQL client, the
  Jira REST v3 client, `reconcile`, `SyncDuty`.
- The injectable `transport` seam (`TransportFn` signature, `_default_transport` built on
  `_http.py`'s `open_url`) — this is what let the original implementation's test suite run with
  zero live network calls and no new mocking dependency; keep it exactly as designed.
- Auth delegation via `keys.HostScopedCredential`/`resolve_headers` for every outbound call,
  with zero changes to `_http.py` — this worked correctly and must not change.
- The GraphQL `_GET_PROJECT_ITEM_QUERY`/`_UPDATE_PROJECT_ITEM_FIELD_MUTATION` shapes and the
  Jira two-step transitions lookup (`GET` transitions, match `to.name`, `POST` the matched
  `id`) — verified correct against this spec's Design Notes' golden examples; keep verbatim.
- The `DutyResult`-with-`details={"decision": ...}` return shape from `reconcile` (no separate
  parallel result type) — a good, simple API; keep it.
- Config validation structure (`SyncConfigError` for a missing/malformed file or section) — the
  overall shape is sound; deeper field-level validation gaps found in this review pass are
  `patch`-classified (moot for this loopback per the workflow's cascading rule) and may resurface
  for direct patching on a future review pass rather than requiring another spec amendment.
- Test structure: conformance tests organized one-per-I/O-Matrix-row using a fake `transport`
  returning canned JSON — keep this approach; the two new algorithm steps need their own test
  cases added (unrelated-field-edit-is-a-no-op, value-already-matches-is-a-no-op), and the
  redirected/dry-run tests' fixture data may need `updated_at`/sync-point values adjusted to
  stay consistent with the corrected algorithm.

### 2026-08-10 — Review pass 5 (bad_spec)

**Triggering finding:** (Blind Hunter, HIGH — independently re-confirming Review pass 2's own
`[high][bad_spec]` "(would-be)" finding, recorded in that pass's log but never actually applied:
pass 3's re-derivation addressed the *other* two open threads from pass 2 — AD-1's trigger
mechanism intent_gap and the checkout-topology bad_spec — but silently dropped this third one)
point (2)'s "capture the timestamp after the write" fix from review pass 1 is necessary but not
sufficient: writing the sync-point field is itself a write to the same item, and unconditionally
advances that item's own `updated_at` past the sync-point value the write just recorded. From the
second reconcile of any previously-synced pair onward, both `gh_stale` and `jira_stale` evaluate
`False` regardless of whether either side has actually changed since — permanently misrouting
every subsequent divergence into the "real conflict" branch, where AD-4's GitHub-wins default
fires unconditionally. Traced by hand against `reconcile`'s exact write ordering: for a pair
converged by reconcile N, any genuine Jira-only status change before reconcile N+1 gets silently
overwritten back to GitHub's stale value — point (1)'s value-equality short-circuit only rescues
the case where both sides still happen to hold the same value, not this one. This directly
inverts the story's own headline capability (CAP-1, bidirectional propagation) for exactly the
"Jira changed, GitHub didn't" direction, on every use past the first.

**What was amended:** the "Reconcile algorithm" block under Design Notes — added point (3), a
fixed `SYNC_POINT_GRACE` tolerance (`timedelta(seconds=30)`) added to both staleness comparisons,
absorbing the sync-point write's own self-inflicted `updated_at` advance without reopening the
loop guard for a genuine subsequent change (which, being a real, separate edit, lands outside the
30s window on any realistic reconcile cadence). Point (2)'s commentary corrected to stop claiming
point (1) alone "catches" the residual imprecision — it doesn't, for exactly the differing-values
case this bug depends on. No change to Intent, Boundaries & Constraints, or the I/O & Edge-Case
Matrix — all three remain accurate; this is an algorithm-precision gap in Design Notes, same class
as pass 1's, not a boundary or scenario gap.

**Known-bad state avoided:** a "bidirectional" sync that silently degrades to one-directional
(GitHub-only) after the very first successful convergence of any pair, clobbering legitimate
Jira-side changes with no error, no log the operator would think to check, and no test catching
it (the existing suite's fixtures use multi-day timestamp gaps that never exercise the
sub-minute self-write window this bug lives in).

**KEEP instructions (re-derive faithfully, do not redesign):** everything from review pass 1's
KEEP list still holds verbatim (module shape, transport seam, auth delegation, GraphQL/REST wire
shapes, `DutyResult` return shape, config validation structure, test structure) — nothing about
those changed. Additionally preserve, unchanged, every implementation-level fix review pass 3
already landed on top of that baseline: the `isinstance`/defensive guards on
`github_graphql_request`'s payload, `get_jira_issue`'s status field, and
`transition_jira_issue`'s transitions list; the reciprocal-link check in `_read_both_sides`; the
`field_overrides` key validation against a known-fields set; `jira_project_key` enforcement
across all three `_read_both_sides` paths; `load_config`'s `OSError`/`UnicodeDecodeError`
wrapping; the module docstring's `ARCHITECTURE-SPINE.md` reference (not the gitignored spec
path); the workflow templates' `.netrc` `rm -f`/`touch`/`chmod 600`-before-`echo` ordering; and
the `test_sync_duty.py` / Jira-timestamp-without-colon test coverage. Only the two staleness-
comparison lines, their surrounding comments, and the `timedelta` import change; add tests
proving (a) a genuine change landing inside `SYNC_POINT_GRACE` of the last sync is deferred (not
lost) rather than clobbered, and (b) the same change is correctly picked up once safely outside
the window on the next reconcile.

## Review Triage Log

### 2026-08-09 — Review pass 1
- intent_gap: 0
- bad_spec: 2 (high 2, medium 0, low 0)
- patch: 11 (high 0, medium 5, low 6)
- defer: 4 (high 0, medium 1, low 3)
- reject: 2
- addressed_findings:
  - `[high]` `[bad_spec]` Sync-point timestamp captured before the write(s) it bookmarks,
    permanently defeating the AD-5 loop guard after the first real write — Design Notes'
    reconcile algorithm amended to capture the timestamp strictly after the write.
  - `[high]` `[bad_spec]` No value-equality short-circuit before pushing, so an unrelated field
    edit (item-level, not field-level, staleness per AD-5) drives a live push attempt for a
    value the destination already holds, commonly hard-failing on Jira workflows with no
    self-transition — Design Notes' reconcile algorithm amended to add the check.

Findings recorded but NOT acted on this pass (moot per the cascading rule — bad_spec found,
code is being reverted and re-derived; patch/defer items may resurface for direct action on the
next review pass if still present in the re-derived code):
- `[medium]` `[patch]` `load_config` doesn't catch `yaml.YAMLError` for malformed YAML syntax.
- `[medium]` `[patch]` `load_config` only checks required fields for presence, not for being a
  non-empty string (a `null`/`""` value passes through).
- `[medium]` `[patch]` `get_project_item`/`get_jira_issue` index the API response directly
  (`node["id"]`, `fields["updated"]`) without a defensive `.get()` + named `SyncAPIError`,
  inconsistent with `keys.load_inventory`'s own `KeyError` → `InventoryError` precedent.
- `[medium]` `[patch]` The both-identifiers-given path only checks each link field is non-empty,
  never that the two actually reference each other (corroborated by both reviewers).
- `[medium]` `[patch]` A transient network `OSError` isn't caught by `SyncDuty.run()`, escalating
  routine network flakiness to `cli.main()`'s crash boundary instead of a duty-level failure.
- `[low]` `[patch]` `field_overrides`/`user_mapping` given as a falsy non-dict (`[]`, `""`, `0`)
  is silently coerced to `{}` instead of raising, because the `or {}` default runs before the
  `isinstance` check.
- `[low]` `[patch]` `field_overrides["status"]` accepts any non-`"jira"` value (including typos)
  and silently reverts to default authority instead of validating against a known set.
- `[low]` `[patch]` `_parse_timestamp` raises an uncaught `TypeError` on a timezone-naive
  hand-edited sync-point value instead of a named failure.
- `[low]` `[patch]` The workflow templates never pass `--config` explicitly, relying on
  undemonstrated implicit `repo_root()` walk-up resolution in the nested-checkout topology they
  imply.
- `[low]` `[patch]` The `jira-to-github.yml.template`'s `repository_dispatch` listener doesn't
  validate the dispatched `jira_key` belongs to the configured project before reconciling.
- `[low]` `[patch]` An unrecognized top-level key in `sync-config.yaml` (e.g. a typo'd section
  name) is silently ignored rather than rejected.
- `[medium]` `[defer]` A write failure partway through (status pushed, sync-point write fails)
  leaves inconsistent state with no rollback — same accepted-risk class as `keys.rotate_identity`'s
  documented non-atomicity; worth documenting as a deliberate limitation, not a quick patch.
- `[low]` `[defer]` GitHub `fieldValues(first: 50)` has no pagination; boards with 50+ custom
  fields could silently miss the configured field. Narrow, needs real pagination work.
- `[low]` `[defer]` TOCTOU race between `reconcile`'s read and its write — inherent to the
  reconcile-without-locking design, needs optimistic concurrency to fix properly.
- `[low]` `[defer]` Three sequential HTTP writes per convergence instead of batched/aliased
  GraphQL calls — a latency/rate-limit cost, not a correctness bug once the two bad_spec fixes
  land.
- `[low]` `[reject]` "Jira host/`.netrc` mismatch silently produces an unauthenticated request"
  — does not hold up; every Jira client function checks `status >= 400` and raises a named,
  loud `SyncAPIError` on a 401.
- `[low]` `[reject]` "AD-numbers/Design Notes are unverifiable from this diff alone" — an
  artifact of the reviewer's intentionally diff-only, cold-context scope, not a defect in the
  change; verified directly against source documents earlier in this workflow run.

### 2026-08-09 — Review pass 2
- intent_gap: 1 (high 1)
- bad_spec: 2 (high 2)
- patch: 12 (medium 5, low 7)
- defer: 3 (medium 2, low 1)
- reject: 0
- addressed_findings:
  - none (intent_gap present — all lower-priority findings, including the two bad_spec ones,
    are moot this pass; see HALT result below for the intent_gap finding itself)

Full classification, recorded for continuity (none of the below were acted on this pass):
- `[high]` `[intent_gap]` **Root cause is inside `<intent-contract>`.** The Intent section's
  Approach sentence ("wired to a `project_v2_item`-triggered GitHub Actions workflow template")
  restates the parent architecture's Stack table verbatim (`GitHub Actions (`on: project_v2_item`
  webhook)`) — and this claim is factually wrong. Verified directly against GitHub's own "Events
  that trigger workflows" documentation (fetched this pass) and corroborating web search: neither
  `project_v2_item` nor `projects_v2_item` is a valid workflow `on:` trigger event. GitHub's
  `projects_v2_item` webhook exists but can only be subscribed to at the organization level via a
  GitHub App or a webhook endpoint external to Actions — reaching a `.github/workflows/*.yml` file
  requires that external receiver to call `repository_dispatch` itself (the same mechanism this
  story already uses for the Jira→GitHub direction). Fixing this requires a genuine architecture
  decision (what serves as the external receiver — a dedicated GitHub App, a serverless function,
  something else — each with different hosting/credential/cost implications the architecture
  hasn't addressed) with more than one non-obvious answer, which is exactly what makes this
  `intent_gap` rather than `bad_spec`: the claim lives inside the read-only `<intent-contract>`
  block, inherited from the architecture, not something this story's own Design Notes can silently
  correct.
- `[high]` `[bad_spec]` (would-be) The reconcile algorithm's pass-1 fix was itself insufficient:
  because the sync-point field lives on the SAME item whose `updated_at` it must bound (AD-2 — no
  sidecar store), and because writing that field is itself a write that bumps `updated_at` again,
  the item's `updated_at` reads as "newer than its own sync point" *permanently* after the first
  real write, not just for one extra round. Traced by hand this pass: this doesn't just cause a
  harmless extra no-op (which the value-equality short-circuit from pass 1 does correctly catch)
  — it causes every *subsequent* divergence to be misclassified as a "conflict," where default
  GitHub-wins authority silently overwrites a genuinely newer Jira change with GitHub's old,
  unrelated value. A correct fix likely needs a grace/tolerance window on the AD-5 time comparison
  (`updated_at <= sync_point + grace`, still literally "time-based... own updated_at vs. own
  recorded sync point," so architecture-compliant) sized above the observed write-cascade latency,
  documented as a deliberate, bounded trade-off (an edit landing inside the grace window is
  deferred to the next trigger for that item, not lost). Not written up as a full Design Notes
  amendment this pass — moot under the intent_gap cascade, and revisiting it makes more sense
  once the intent_gap above is resolved and the trigger mechanism (hence the write-cascade shape)
  is actually known.
- `[high]` `[bad_spec]` (would-be) Both GitHub Actions workflow templates' only `actions/checkout`
  step overrides `repository: <your-org>/local-recipes`, so the target (external) repo — whose
  `.steward/sync-config.yaml` the templates then reference by relative path — is never actually
  checked out anywhere. Every deployment following the README as written would fail on the first
  run with "sync config not found." Also moot under the cascade; the correct checkout topology
  (default implicit checkout of the target repo + an explicit second checkout of `local-recipes`
  into a named subdirectory to install `steward` from) should be specified once the trigger
  mechanism above is settled, since that decision affects what else the templates need to do.
- `[medium]` `[patch]` `reconcile(github_item_id="", jira_issue_key=None)` crashes with an
  unhandled `AttributeError` — the entry guard checks `is None` (so `""` passes it) while the
  fetch logic below checks truthiness (so `""` is treated as absent), leaving both `gh`/`jira`
  unset before one is unconditionally dereferenced.
- `[medium]` `[patch]` The both-identifiers-given path still only checks each side's link field
  is non-empty, never that they reference each other (corroborated by both reviewers, both
  passes).
- `[medium]` `[patch]` Malformed-but-2xx API responses (missing `data`/`fields`/`updated` keys)
  raise raw, uncaught `KeyError`s instead of a named `SyncAPIError` — corroborated by both
  reviewers this pass, and a repeat of a pass-1 finding.
- `[medium]` `[patch]` `_default_transport` only catches `urllib.error.HTTPError`, not the
  broader `URLError` (DNS/connection/timeout) — refines pass 1's "OSError not caught" finding.
- `[medium]` `[patch]` Required config fields are checked for key-presence only, not for being
  non-empty — repeat of a pass-1 finding, still present.
- `[low]` `[patch]` `issue_key` (which can originate from an external webhook payload) is
  interpolated unescaped into Jira REST URLs — corroborated by both reviewers.
- `[low]` `[patch]` The new `.gitignore` entry only protects local-recipes' own working tree;
  the real `.steward/sync-config.yaml` this story cares about lives in the external target repo,
  where this entry has no effect and no equivalent is documented.
- `[low]` `[patch]` `update_jira_issue_fields`'s docstring claims success is specifically `204`;
  the code accepts any status `< 300`.
- `[low]` `[patch]` `field_overrides["status"]` still accepts any non-`"jira"` value including
  typos, silently reverting to default authority — repeat of a pass-1 finding.
- `[low]` `[patch]` A timezone-naive hand-edited sync-point value raises an uncaught `TypeError`
  on comparison — repeat of a pass-1 finding.
- `[low]` `[patch]` An unset GitHub status field (`None`) used as a push source produces a
  confusing "no transition to None" error instead of a named, clearer failure.
- `[low]` `[patch]` `jira_base_url` without a URL scheme yields an empty/`None` hostname fed
  into `HostScopedCredential` — likely already caught by that class's own `__post_init__`
  validation (raises `TypeError`/`ValueError`), but with a generic rather than config-specific
  message.
- `[medium]` `[defer]` The value write and the two sync-point writes aren't atomic; a failure
  after the value write but before both sync-point writes leaves the two sides' sync-points
  diverged — same accepted-risk class as `keys.rotate_identity`'s documented non-atomicity,
  repeat of a pass-1 finding.
- `[medium]` `[defer]` No concurrency guard around the read-decide-write sequence; two
  overlapping `reconcile` invocations for the same pair can interleave — repeat of a pass-1
  finding (TOCTOU race).
- `[low]` `[defer]` `fieldValues(first: 50)` still has no pagination — repeat of a pass-1
  finding.

### 2026-08-09 — Review pass 3

Re-derived implementation of the corrected spec (AD-1's reversal to `schedule`-default landed
separately in main via PR #378 before this pass began; the `<intent-contract>` above already
carries "CORRECTED 2026-08-09" reflecting it). No `intent_gap` or `bad_spec` findings this pass —
every finding below is implementation-level and `patch`/`defer`/`reject`-classified.

- intent_gap: 0
- bad_spec: 0
- patch: 11 (high 0, medium 7, low 4)
- defer: 4 (high 0, medium 0, low 4)
- reject: 3
- addressed_findings:
  - `[medium]` `[patch]` `load_config`'s file `open()`/read was unguarded against
    `OSError`/`UnicodeDecodeError` (only `yaml.YAMLError` was caught), letting a permission or
    encoding failure escape `SyncDuty.run()`'s `except SyncConfigError` and crash to
    `cli.main()`'s internal-error boundary instead of a named `DutyResult` — now wrapped,
    mirroring `deploy._tracked_ledger_refusal`'s own precedent for the same distinction.
  - `[medium]` `[patch]` `github_graphql_request` called `payload.get("errors")` on a JSON body
    that could be valid-but-non-dict (a bare list/string/null from a 2xx response), raising an
    unhandled `AttributeError` that skipped every caller's `except SyncError` boundary — now
    guarded with an explicit `isinstance(payload, dict)` check raising `SyncAPIError`.
  - `[medium]` `[patch]` `get_jira_issue`'s `status=(fields.get("status") or {}).get("name")`
    raised an unhandled `AttributeError` if Jira's `status` field was present but not a mapping
    — now reads as `None` (an unknown status) rather than crashing.
  - `[medium]` `[patch]` `transition_jira_issue`'s transitions loop raised an unhandled
    `AttributeError` if the `"transitions"` key resolved to a non-list value — now raises a
    named `SyncAPIError` up front, and each loop entry is defensively coerced to `{}` if it
    isn't itself a mapping.
  - `[medium]` `[patch]` `_read_both_sides` never verified the two sides' link fields point back
    at each other reciprocally, in any of its three branches — a mismatched/asymmetrically-linked
    pair was silently treated as valid and could cross-propagate status to the wrong item. This
    was already logged as `[medium][patch]` in both Pass 1 and Pass 2 but never actually applied
    (moot both times under the cascading rule); now fixed with an explicit reciprocal check.
  - `[medium]` `[patch]` `field_overrides` validated only the override VALUE (`"jira"`), never
    the KEY — a typo'd field name (e.g. `statuz`) loaded successfully and was silently ignored,
    contradicting the module's own "a typo must fail loud" principle. Now validated against a
    known-fields set.
  - `[medium]` `[patch]` `jira_project_key` was a required config field that was loaded but never
    used to validate anything — a `--jira-issue`/resolved-link value for an unrelated project was
    processed with no rejection. Generalizes a Pass-2 finding that was scoped only to the
    `repository_dispatch` listener template; now enforced in `_read_both_sides` itself for every
    path (direct `--github-item`, direct `--jira-issue`, and both-given).
  - `[low]` `[patch]` `sync.py`'s module docstring cited the Tier-3, gitignored
    `_bmad-output/implementation-artifacts/spec-8-1-bidirectional-propagation.md` path directly
    — a dangling reference in every other clone/worktree once that run's implementation
    artifacts are gone. No sibling duty module (`keys.py`/`deploy.py`/`budget.py`) does this; now
    reworded to reference the tracked `ARCHITECTURE-SPINE.md` instead.
  - `[low]` `[patch]` Both workflow templates' `.netrc` setup appended credentials before running
    `chmod 600`, leaving a brief default-permission window and allowing duplicate `machine`
    stanzas to accumulate across repeated runs — now `rm -f`/`touch`/`chmod 600` before the
    `echo >>`.
  - `[low]` `[patch]` No test exercised `SyncDuty.run()` directly (only `load_config`/`reconcile`
    were tested via direct function calls) — the AC "bare `steward sync` degrades to `ok=True`
    naming available verbs" had no test proving it. Added `tests/conformance/test_sync_duty.py`
    covering the no-verb degrade, a config-load failure via `main()`, and full CLI-arg threading
    (`--github-item`/`--config`/`--dry-run`) end-to-end.
  - `[low]` `[patch]` No test fixture exercised Jira's real `updated` timestamp wire format
    (offset without a colon, e.g. `+0000`) — added a fixture-driven test proving `_parse_timestamp`
    handles it via `reconcile`'s own staleness computation.
- Findings recorded but NOT acted on this pass (deferred to `deferred-work.md`):
  - `[low]` `[defer]` `fieldValues(first: 50)` has no pagination — repeat of a Pass 1/2 finding,
    never actually appended to the ledger before now (both passes were moot under the cascading
    rule); appended this pass.
  - `[low]` `[defer]` A GitHub field misconfigured as a single-select instead of TEXT reads as
    `None` rather than a clear diagnostic — needs a new GraphQL fragment and a message-design
    decision, more than a trivial patch.
  - `[low]` `[defer]` No rate-limit/backoff/retry handling on any GitHub/Jira API call.
  - `[low]` `[defer]` `user_mapping` values aren't type-checked — low impact, the field is
    unused/reserved for a future assignee-sync story.
- Findings rejected (dropped silently): unpinned `ref:` on the workflow templates' `local-recipes`
  checkout (templates are explicitly operator-customized documents, already TODO-heavy); the
  schedule/manual path syncing only one hardcoded example item (already prominently labeled as a
  TODO in-template, not a hidden defect); a matched-but-`id`-less Jira transition producing a
  slightly imprecise error message (cosmetic — the failure is still correctly named and
  non-crashing).

### 2026-08-10 — Review pass 4 (verification-repair)

Deterministic verification (`python scripts/spec_surface_check.py`) failed after Pass 3 landed:
`.steward/sync-config.example.yaml` was ungoverned (no spec surface, no allowlist entry). Repaired
by adding it to `spec-pyforge-steward/SPEC.md`'s `surface:` list (that Spec's own "Config file
location" constraint already claimed the `.steward/` dotdir in prose; it just never got a matching
glob) plus a reconciling `.memlog.md` entry — governance metadata only, no application code and no
`<intent-contract>` change. This pass's diff (scoped to that repair, `baseline_revision` recaptured
at the post-Pass-3 commit) was independently reviewed by Blind Hunter + Edge Case Hunter.

- intent_gap: 0
- bad_spec: 0
- patch: 4 (medium 1, low 3)
- defer: 4 (medium 2, low 2)
- reject: 3
- addressed_findings:
  - `[medium]` `[patch]` (Blind Hunter + Edge Case Hunter, corroborated) The repair's own
    `.steward/**` surface glob was a directory-level catch-all — the credential-adjacent dotdir
    this Spec's own Constraints section designates, and this repo already learned the
    too-broad-glob lesson once (the `scripts/**` allowlist split). Narrowed to four per-kind
    entries (`budget.yaml`, `keys-inventory.yaml`, `*.age`, `sync-config.example.yaml`) matching
    the Constraints prose's own enumerated file kinds exactly.
  - `[low]` `[patch]` (Edge Case Hunter) The "Config file location" constraint named only 3 of the
    now-4 file kinds living in `.steward/` — added `sync-config.example.yaml` to that sentence.
  - `[low]` `[patch]` (Blind Hunter) `.memlog.md`'s frontmatter `updated:` timestamp wasn't
    advanced by the new entry, unlike every prior entry in the file's own history — bumped to this
    pass's timestamp.
  - `[low]` `[patch]` (Blind Hunter) The new memlog entry omitted the "Relevant to THIS spec's own
    contract" closing clause every Story-6.x sibling-spec RECONCILES entry uses, and never named a
    CAP or explicitly stated it claims none — added the clause (AD-7 conformance, still generic
    via `test_duty_protocol.py`) and an explicit "No CAP is claimed here" statement.
- Findings recorded but NOT acted on this pass (deferred to `deferred-work.md`):
  - `[medium]` `[defer]` (Blind Hunter) `sync.py` hardcodes `api.github.com` instead of reusing
    `_http.py`'s existing `resolve_github_api_urls()` (built for exactly this, REST+GraphQL, with
    a GitHub Enterprise Server override) — verified real against `_http.py` source; violates this
    story's own governing Spec's AD-1/AD-9. Pre-existing in the already-committed, already-3x-
    reviewed `sync.py`, not caused by this repair pass. The parallel claim for `jira_base_url`
    (below, rejected) does NOT apply here — GitHub already has an existing table row to reuse;
    Jira does not.
  - `[medium]` `[defer]` (Edge Case Hunter + Blind Hunter, corroborated from different angles)
    No detector semantically verifies the `sync` duty's actual architecture (AD-1..AD-9 from
    `architecture-jira-github-projects-sync-2026-08-09`) compliance — `spec-pyforge-steward`'s
    surface/memlog machinery is file-hash drift only, not behavioral/architectural compliance,
    for a capability whose intent is authored by a sibling spec but whose code lives under this
    spec's surface. A structural, repo-wide observation, not specific to this story.
  - `[low]` `[defer]` (Blind Hunter) `spec-jira-github-projects-sync/SPEC.md` still asserts "no
    sync code ... exists anywhere in this repo yet (verified by grep 2026-08-08)" — stale since
    this story shipped `sync.py`. `surface: []` staying empty is correct (files are governed
    elsewhere); only the prose claim is stale.
  - `[low]` `[defer]` (Blind Hunter) `spec-pyforge-steward/SPEC.md`'s "Config file location"
    constraint claims the whole `.steward/` dotdir is "tracked (not gitignored)", but this story's
    own already-committed `.gitignore` entry excludes the operator's real `sync-config.yaml`
    (`.example.yaml` stays tracked) — a narrow, undocumented exception to that constraint's literal
    wording. Predates this repair pass.
- Findings rejected (dropped silently): "AD-9 violation, `jira_base_url` not routed through a
  `_http.py` `resolve_*_urls` table row" and "AD-2 duplicate URL config" (Blind Hunter) — verified
  no such table row exists for Jira in `_http.py`, and the story's own frozen `<intent-contract>`
  explicitly designs `jira_base_url` as an operator-declared `SyncConfig` field (each Jira Cloud
  tenant has a different hostname, unlike GitHub's single fixed public host) — by design, not a
  duplication of anything. "`spec-pyforge-steward/SPEC.md`'s `companions:` list should include the
  jira-sync architecture spine" (Blind Hunter) — inconsistent with this repo's own established
  precedent: none of the Story 6.1–6.3 sibling-spec (`spec-bmad-module-provisioning`) RECONCILES
  entries added that sibling's architecture as a companion of the surface-owning spec either.

### 2026-08-10 — Review pass 5

Cold-context review of the full story diff (baseline `c8503d9def...` — this run's harness
re-invoked `bmad-dev-auto` for this already-`done` story from a fresh worktree unaware of the
prior run's unlanded branch; see the Auto Run Result session note above for how the already-
reviewed commits were recovered and re-verified onto this branch before this pass ran).

- intent_gap: 0
- bad_spec: 1 (high 1)
- patch: 6 (high 1, medium 1, low 4)
- defer: 4 (medium 1, low 3)
- reject: 2
- addressed_findings:
  - none (bad_spec present — all lower-priority findings are moot this pass; see the Spec Change
    Log entry above for the bad_spec finding itself, addressed via a Design Notes amendment and
    the code repair described there, not a full re-derivation from a blank slate — the fix is two
    staleness-comparison lines, their comments, and a `timedelta` import; every other line was
    already independently verified correct across passes 1–4 and is preserved verbatim per the
    Spec Change Log entry's KEEP list, so `step-03`'s "re-derive" was executed as a spec-traceable
    direct edit rather than a wasteful full-file rewrite of otherwise-unchanged, already-reviewed
    code)

Full classification, recorded for continuity (none of the below were acted on this pass):
- `[high]` `[bad_spec]` The sync-point-write-after-value-write fix from pass 1 is still
  insufficient — see the Spec Change Log entry above. Fixed this pass via the `SYNC_POINT_GRACE`
  tolerance.
- `[high]` `[patch]` (Blind Hunter) Both workflow templates install `steward` with a normal,
  non-editable `pip install ./_steward-src/...`, which copies `keys.py` into site-packages
  disconnected from the `_steward-src` checkout tree; `locate_http_module()`'s upward
  parent-walk (executed at import time) can then never find
  `.claude/skills/conda-forge-expert/scripts/_http.py`, so importing `steward.sync` — and hence
  running `steward sync reconcile` at all — raises `RuntimeError` on every invocation. Verified
  directly against `keys.py`'s `locate_http_module`/module-load-time `sys.path` wiring and the
  templates' literal `pip install` line (no `-e`). This is the actual external-repo deployment
  path CAP-1 exists to serve; a one-flag fix (`pip install -e ...`) once the loopback settles.
- `[medium]` `[patch]` (Blind Hunter + Edge Case Hunter, corroborated) No explicit handling for an
  unset/`None` source status: `transition_jira_issue(issue_key, None, ...)` produces a confusing
  "no transition to status None" failure instead of a clear "source status is unset" diagnostic,
  and (Edge Case Hunter) a transitions entry that itself lacks a `to` object could spuriously
  read as a `None == None` match instead of being skipped. Narrow (requires a freshly-linked item
  whose tracked field was never populated) but real and untested.
- `[low]` `[patch]` (Blind Hunter, Edge Case Hunter — repeat of a Pass 1 finding, still present,
  never yet fixed across passes 1–4) `field_overrides`/`user_mapping` given as a falsy non-dict
  (`false`, `0`, `""`, `[]`) is silently coerced to `{}` before the `isinstance` check runs,
  contradicting the module's own "a typo must fail loud" principle.
- `[low]` `[patch]` (Blind Hunter) `_read_both_sides`'s CLI entry point wires `--github-item`/
  `--jira-issue` as a mutually exclusive `argparse` group, so the "both identifiers given"
  reconciliation branch in `sync.py` is unreachable from the actual product surface — dead code
  outside direct API/test use.
- `[low]` `[patch]` (Edge Case Hunter) `get_project_item`'s `fieldValues.nodes` parsing loop has
  no defensive check that `nodes` is a list of mappings; a malformed-but-truthy non-list/non-dict
  API response would raise an uncaught `AttributeError` past the function's documented
  `SyncAPIError`-only contract, rather than the `KeyError`/`TypeError` cases already guarded a few
  lines above.
- `[low]` `[patch]` (Blind Hunter) `_default_transport`'s `HTTPError` branch reads `exc.read()`
  but never closes `exc`, unlike the success path's `with open_url(...)` a few lines above — an
  inconsistent resource-cleanup pattern within the same function.
- `[medium]` `[defer]` (Blind Hunter) Both workflow templates `echo` the Jira API token into
  `~/.netrc` on the runner with no cleanup step at job end — low practical exposure on an
  ephemeral Actions runner, but a real gap versus this repo's own credential-hygiene bar if
  step-debug logging or a later job step ever dumps the filesystem.
- `[low]` `[defer]` (Blind Hunter, Edge Case Hunter — repeat of a Pass 1/2/3 finding, already in
  `deferred-work.md`) `fieldValues(first: 50)` still has no pagination.
- `[low]` `[defer]` (Blind Hunter — repeat of a Pass 3 finding, already in `deferred-work.md`) A
  GitHub field misconfigured as single-select instead of TEXT still reads as `None` with no
  targeted diagnostic.
- `[low]` `[defer]` (Edge Case Hunter — same class as the already-deferred Pass 1 TOCTOU finding)
  No concurrency guard between a `schedule` tick and a near-simultaneous `repository_dispatch` for
  the same item; both would race the same read-decide-write sequence with no lock or
  `concurrency:` group in the templates.
- `[low]` `[reject]` (Blind Hunter) "A freshly-linked pair with no recorded sync-point on either
  side routes to the conflict branch and applies AD-4's GitHub-wins default, potentially
  overwriting a pre-existing Jira status" — this is the frozen `<intent-contract>`'s AD-4 default
  operating exactly as documented (Boundaries & Constraints: "GitHub's value wins unless the
  field carries an explicit override") combined with AD-5's own documented "absent sync_point =>
  NOT stale" rule; surprising to an un-briefed operator, perhaps, but not a deviation from the
  spec.
- `[low]` `[reject]` (Blind Hunter) "The schedule/manual trigger only syncs one hardcoded example
  item" — duplicate of a Pass 3 finding already rejected there (prominently labeled as an
  in-template TODO, not a hidden defect).

### 2026-08-10 — Review pass 6 (reviewing pass 5's own fix)

- intent_gap: 1 (high 1)
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none (intent_gap present — see HALT result below)

- `[high]` `[intent_gap]` **Root cause is inside `<intent-contract>`.** Pass 5's
  `SYNC_POINT_GRACE` fix does not deliver the "deferred, not lost" guarantee its own Design Notes
  and tests claimed. Traced by hand, confirmed against the code: `gh.updated_at`/`jira.updated_at`
  and `gh.sync_point`/`jira.sync_point` are all static, server-recorded values that do not advance
  with the mere passage of wall-clock time — only a NEW write changes them. `reconcile`'s `no_op`
  path (`sync.py` ~786) returns immediately without writing anything. So once a genuine edit lands
  within `SYNC_POINT_GRACE` of the prior sync and gets misread as "still stale" (unchanged), that
  exact same misreading recurs identically on every future reconcile of that item, forever, no
  matter how many scheduled ticks or dispatches fire afterward, until some *unrelated* later edit
  changes one of the compared values — at which point the reconcile that finally detects a
  divergence does so by comparing against the *original*, long-stale `sync_point`, and applies
  AD-4's default (GitHub wins) to the *current* values, silently discarding not just the first
  dropped edit but every Jira-side change made since the last real sync. This is not a narrower
  version of the bug pass 5 fixed — independently re-derived by Blind Hunter in pass 6's review of
  pass 5's own diff, then confirmed by hand-tracing the exact write/no-op paths.
  Root cause: comparing an item's own aggregate `updated_at` against a marker stored as a field ON
  THAT SAME ITEM cannot, for any grace tolerance, distinguish "my own sync-point write's
  self-inflicted advance" from "a coincidental genuine edit landing in the same window" — both
  produce an identical, small `(updated_at − sync_point)` gap by construction. No grace value
  removes this ambiguity; it only resizes the window during which it resolves (silently, and
  wrongly) to "unchanged." This traces to the frozen Intent's own literal mechanism ("compares
  each side's `updated_at` against its own recorded sync point") combined with AD-2 (no sidecar
  store) — Design Notes cannot patch its way out of a comparison basis that is structurally unable
  to always distinguish these two cases without either (a) a sidecar/adjacent store (forbidden by
  AD-2), (b) a per-*field* (not per-item) last-changed signal — asymmetrically available: Jira
  exposes one via its changelog API, GitHub Projects V2 does not expose one for custom field
  values as far as this session could determine — or (c) replacing the timestamp comparison with a
  last-synced-*value* comparison (immune to this class of self-interference entirely, since
  writing a bookkeeping field doesn't change the tracked field's own value), which is a materially
  different mechanism than "updated_at vs. sync point." Each of (a)/(b)/(c) is a genuine,
  non-obvious architecture decision with real trade-offs — exactly what makes this `intent_gap`
  rather than a further `bad_spec` loopback, matching this story's own pass 2 precedent for the
  same distinction.

### 2026-08-10 — Review pass 7 (post-reissue implementation)

Cold-context review of this session's diff (baseline `c41ed99363...` — this run's actual
starting HEAD, which already carried the pre-fix `sync.py` landed by PR #383; see the Auto Run
Result session note for the full discovery). Blind Hunter and Edge Case Hunter both reviewed the
same ~1400-line diff independently, then empirically ran the test suite and
`spec_surface_check.py` themselves before reporting.

- intent_gap: 0
- bad_spec: 0
- patch: 7 (medium 3, low 4)
- defer: 3 (medium 3, low 0)
- reject: 3
- addressed_findings:
  - `[medium]` `[patch]` (Blind Hunter + Edge Case Hunter, corroborated) The true early no-op
    return's `details` dict omitted the `"baseline"` key present on every other return path, and
    the dry-run return's `details` also omitted it — a caller reading `details["baseline"]`
    unconditionally on `decision == "no_op"` would `KeyError` on the true-no-op/dry-run paths.
    Fixed: `details` now always includes `"baseline"` (defaulting to `None`, overwritten once
    actually written), giving every return path one consistent shape.
  - `[medium]` `[patch]` (Blind Hunter + Edge Case Hunter, corroborated) The true early no-op
    summary omitted `dry_run=...`, unlike every other decision branch's summary — a log/summary
    consumer couldn't tell from that one branch's text whether the call was a dry run. Fixed:
    summary now includes `dry_run={dry_run}`.
  - `[medium]` `[patch]` (Blind Hunter) `_read_both_sides`'s "both identifiers given" branch had
    zero test coverage under the new baseline mechanism (only the two single-identifier paths and
    the mismatched-reciprocal-link case were exercised). Added
    `test_both_identifiers_given_and_reciprocal_reconciles_normally`.
  - `[medium]` `[patch]` (Edge Case Hunter) `_parse_baseline`'s `if not raw` guard treated any
    falsy value — not just `None`/`""` — as "never synced," so a baseline field genuinely
    misconfigured to point at a non-text field (e.g. a Jira Number/Checkbox field returning
    `0`/`false`) would silently read as a first link instead of raising a named config-mismatch
    error. Narrowed to `if raw is None or raw == ""`; a falsy-but-non-string value now falls
    through to the JSON parse, which raises `SyncAPIError`. Added
    `test_parse_baseline_rejects_a_falsy_non_string_value_instead_of_treating_it_as_never_synced`.
  - `[low]` `[patch]` (Blind Hunter) The AD-4 conflict-authority branch read
    `config.field_overrides.get("status")` as a bare string literal instead of the `_TRACKED_FIELD`
    constant this same diff introduces two lines away (whose own comment claims it "matches
    `field_overrides`'s own `_VALID_OVERRIDE_FIELDS`") — no behavior change since the constant's
    value is `"status"`, but a real inconsistency inside a hunk this diff directly rewrote. Fixed.
  - `[low]` `[patch]` (Blind Hunter) `_serialize_baseline`'s docstring claimed it enforces the
    ceiling "before any write is attempted" — true only of the two baseline writes; the
    cross-system tracked-value write (the Jira transition or GitHub field update) has, in the
    general case, already completed by the time this function runs. Docstring corrected.
  - `[low]` `[patch]` (Blind Hunter) The spec's own Design Notes pseudocode described the baseline
    refresh as a `for side in (github, jira): compute; write` loop, which (if taken literally)
    would let one side's baseline get written before the other side's ceiling check fails,
    leaving an inconsistent state. The actual code computes both serialized baseline strings
    first, before writing either — safer than the literal pseudocode, and already proven by
    `test_baseline_exceeding_the_field_size_ceiling_is_a_named_failure_after_the_value_push`'s own
    assertions that neither baseline is written on a ceiling failure. Design Notes rewritten to
    describe the actual (safer) ordering rather than the literal per-side loop.
- Findings deferred to `deferred-work.md` (real, but not this session's to resolve — see the
  ledger for full evidence):
  - `[medium]` `[defer]` (Blind Hunter) Whether GitHub's real `updateProjectV2ItemFieldValue`
    accepts an explicit `text: null` as "clear the field" is unverified against a live board — the
    new field-cleared test proves the decision logic, not the real API's actual behavior.
  - `[medium]` `[defer]` (Blind Hunter) `_GITHUB_BASELINE_FIELD_CEILING = 1024` remains an
    explicitly unverified placeholder (already documented in-code); if the real limit is lower,
    the failure mode degrades to a generic `SyncAPIError` instead of the clean
    `SyncBaselineTooLargeError` this mechanism exists to produce.
  - `[medium]` `[defer]` (Edge Case Hunter) If the two sides' baseline maps ever silently diverge
    from each other (via the already-accepted value-write/baseline-write non-atomicity),
    `reconcile` has no way to detect or repair it — a permanently "healthy" no-op that never
    self-heals. This is the specific consequence of a risk already accepted in this story's own
    Design Notes and `reconcile`'s in-code comment, logged as `[medium][defer]` in this Review
    Triage Log across multiple earlier passes but never actually appended to the ledger until now.
- Findings rejected (dropped silently):
  - (Blind Hunter) "Renaming `sync_point_field_id` to `baseline_field_id` in
    `.steward/sync-config.example.yaml` is a breaking config-shape change with no migration note"
    — no real deployment exists to migrate: PR #389's own risk analysis already established
    `sync.py` has zero non-test callers and Epic 8 is greenfield with nothing consuming it, so no
    operator has ever configured a live board under the old key names.
  - (Edge Case Hunter) "A baseline field still holding the pre-rename ISO-8601 sync-point string
    would raise `SyncAPIError` on every reconcile until manually cleared" — same non-issue as
    above (no real deployment exists to hold a stale value), and the failure mode described (a
    loud, named error) is the correct, by-design behavior anyway, not a defect.
  - (Blind Hunter) "Jira's 255-char ceiling is checked via Python `len()` (codepoint count), which
    could diverge from a byte-limited database column under some collation" — speculative; Jira
    Cloud's documented limit is character-based, not byte-based, and no evidence was found that
    this assumption is wrong.

## Design Notes

**Reconcile algorithm** (`reconcile`, pure decision logic — `dry_run`/no-op gate the writes at
the bottom). **Rewritten 2026-08-10 for the re-issued contract** (AD-5's third amendment,
architecture `status: final`) — this replaces every prior "Reconcile algorithm" revision
wholesale; nothing below is a patch on the timestamp mechanism, because the timestamp mechanism
is gone. `FIELD = "status"` is this story's one tracked field throughout (matches
`field_overrides`'s own `_VALID_OVERRIDE_FIELDS`).

```
gh, jira = read_both_sides(github_item_id, jira_issue_key, config)   # resolves the missing id via the link field
if gh.link is empty or jira.link is empty: return ok=False, "unlinked: <which side>"

# AD-5 (amended) / jira:AD-10: a side has changed when its current tracked-field value differs from
# the value its OWN baseline map records for that field. _MISSING is a sentinel distinct from
# None -- an absent key means "never synced" (jira:AD-10 rule 1: not a loop candidate, reconcile as
# a first link); a present key holding None means "synced, and was an explicit clear" (jira:AD-10
# rule 2). Collapsing those two would make a deliberate clear indistinguishable from a field the
# engine has never seen -- exactly the trap jira:AD-10 exists to name.
gh_base    = gh.baseline.get(FIELD, _MISSING)
jira_base  = jira.baseline.get(FIELD, _MISSING)
gh_changed   = gh_base   is _MISSING or gh.status   != gh_base
jira_changed = jira_base is _MISSING or jira.status != jira_base

if not gh_changed and not jira_changed:
    return no_op, ok=True   # neither side diverged from its own baseline -- zero writes, baseline untouched

if gh_changed and not jira_changed:      decision, target_value = PUSH_TO_JIRA,   gh.status
elif jira_changed and not gh_changed:    decision, target_value = PUSH_TO_GITHUB, jira.status
else:                                     # both changed -> AD-4 conflict authority (github wins unless field_overrides)
    decision, target_value = (PUSH_TO_GITHUB, jira.status) if field_overrides.status == "jira" \
                              else (PUSH_TO_JIRA, gh.status)

# Convergence check -- still required, now for a narrower reason than the mechanism it replaces.
# Two sides can independently change to the SAME new value (both diverge from their own stale
# baseline, but agree with each other); AD-4's authority pick would otherwise still be reported
# as a "push", so this catches "the destination already holds target_value" and downgrades to
# no_op. It is NOT a workaround for coarse item-level staleness (the old item-level/field-level
# problem the prior mechanism needed this same check to survive) -- the new per-field value
# comparison above is already field-precise and has no such failure mode on its own.
if target_value == current_dest_value(decision, gh, jira):
    decision = no_op   # but NOT the early return above -- baseline still needs refreshing below

if dry_run:
    report the decision; make NO write calls, refresh nothing
    return

if decision != no_op:
    apply the ONE cross-system write (push_to_jira -> transition_jira_issue; push_to_github -> update_project_item_field)
    # (may raise -- a duty-level failure; baseline is never touched on a failed push)

# Baseline refresh -- runs whenever execution reaches this point (i.e. NOT the true early no_op
# above), whether or not a live write just happened. This is what makes the "both changed to the
# same value" row correct: no API write occurs, but both baselines were stale and must still be
# corrected, or every future reconcile of this pair would see it as "changed" forever.
#
# Both sides' serialized baseline strings are computed FIRST, before either write is attempted --
# not computed-and-written one side at a time. This is deliberately stricter than a naive
# per-side loop: if either side's map would exceed ITS ceiling, NEITHER baseline field is
# written, avoiding an inconsistent state where one side's baseline advances but the other's
# doesn't because a later ceiling check failed after an earlier write already succeeded.
new_gh_map = serialize_baseline({**gh.baseline, FIELD: target_value})    # raises SyncBaselineTooLargeError if oversized
new_jira_map = serialize_baseline({**jira.baseline, FIELD: target_value})  # (computed before EITHER write below)
write new_gh_map to github's baseline field
write new_jira_map to jira's baseline field
    # (either write may raise -- reported as "<decision> but failed refreshing baseline"; same
    # accepted non-atomicity class as keys.rotate_identity's documented partial-completion state
    # -- the cross-system VALUE write above may already have committed even if this step fails)
```

**Baseline serialization & field-size ceiling** (AD-2/jira:AD-10's documented escape hatch to Mode
B): `serialize_baseline` is `json.dumps(map, sort_keys=True, separators=(",", ":"))`, then
compared against a per-vendor ceiling constant before any write is attempted:
- `_JIRA_BASELINE_FIELD_CEILING = 255` — Jira Cloud's "Text Field (single line)" custom field
  type is hard-capped at 255 characters at the database level (well-documented; a write past
  this limit is silently rejected by Jira's own REST API, which is why this module must catch it
  first rather than let that silent failure masquerade as success).
- `_GITHUB_BASELINE_FIELD_CEILING = 1024` — GitHub Projects V2 text fields have **no publicly
  documented character ceiling** (verified by search against GitHub's own GraphQL reference and
  community discussions, 2026-08-10: none exists). This is a conservative, explicitly unverified
  placeholder, not a confirmed vendor limit — re-verify against a live board before relying on
  it, per this story's own Boundaries & Constraints.

Exceeding either ceiling raises `SyncBaselineTooLargeError` (a `SyncError` subclass) naming the
side and the overage; it is never a licence to fall back to a sidecar store.

**GitHub GraphQL mutation shape** (the one non-obvious wire format — reuse verbatim, don't
reinvent field names):

```graphql
mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!) {
  updateProjectV2ItemFieldValue(
    input: { projectId: $projectId, itemId: $itemId, fieldId: $fieldId, value: $value }
  ) { projectV2Item { id } }
}
```

**Jira transition call** — two-step (Jira transitions are by ID, not by name): `GET
/rest/api/3/issue/{key}/transitions` to find the transition whose `to.name` matches the target
status string, then `POST` the same endpoint with `{"transition": {"id": "<found id>"}}`. If no
transition matches, that is the "target API rejects the pushed value" I/O Matrix row — return
`ok=False` naming the unmatched status, never guess the nearest transition.

**Known vendor defect** (already named by the architecture, repeated here because it affects
this story's own write path): `updateProjectV2ItemFieldValue` can update the data correctly
while leaving the Projects V2 board's grouping index stale — a card is logically moved but
looks stuck until a human drags it. This is expected; do not treat a stale board view as a
failed write, and do not add a "verify the UI moved" check anywhere in this story's tests.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Live-pair demonstration (CAP-1's literal acceptance bar — "against a live GitHub Projects V2
  board and a live Jira Cloud project"): once an operator provisions a real external board +
  project with the fields `SyncConfig` expects, sets `GITHUB_TOKEN`/`GH_TOKEN` and a Jira
  `.netrc` entry, and installs the two workflow templates into that external repo, moving a
  card / transitioning an issue should reach the other side within the Action run's normal
  latency. This cannot run inside this unattended build — no live board or credentials exist in
  this environment — and is the operator's documented follow-up
  (`docs/reference/sync-jira-github-workflow-templates/README.md`), not a gate on this story's
  completion.


## Auto Run Result

Status: done

**Summary.** This session resumed an already-implemented, already-committed story (all Tasks &
Acceptance from Pass 3 were `[x]`, HEAD at `b1048105be`) whose deterministic verification failed
on `python scripts/spec_surface_check.py`: `.steward/sync-config.example.yaml` (a new tracked
file Story 8.1 added) had no spec surface and no allowlist entry. Diagnosed and repaired as a
governance-metadata gap, not an implementation gap: `spec-pyforge-steward/SPEC.md` already claims
the `.steward/` dotdir in its "Config file location" Constraints prose but never had a matching
`surface:` glob. No code, tests, or the frozen `<intent-contract>` were touched.

**Files changed (this pass, commit `4953d427429711ad16c654264ae20a183c549815`):**
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md` —
  added four per-kind `surface:` globs (`budget.yaml`, `keys-inventory.yaml`, `*.age`,
  `sync-config.example.yaml`) under `.steward/`, and named the fourth file kind in the "Config
  file location" constraint sentence.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`
  — appended a `(change) RECONCILES ...` entry naming the 7 Story 8.1 files landing under this
  Spec's surface (clears the `[drift-presumed]` informational noise for all 7); bumped `updated:`.

**Review findings (Pass 4, Blind Hunter + Edge Case Hunter on this pass's diff only):** 0
intent_gap, 0 bad_spec, 4 patch (applied: narrowed the glob per corroborated feedback, named the
4th file kind, bumped the memlog timestamp, added the missing "relevant to this spec's own
contract" clause), 4 defer (appended to `deferred-work.md`: `sync.py` bypasses `_http.py`'s
existing `resolve_github_api_urls()` for GitHub calls; no semantic architecture-compliance
detector exists for a sibling-spec-owned capability living under this spec's surface; the sibling
`spec-jira-github-projects-sync/SPEC.md` has a stale "no sync code exists" claim; the "Config file
location" constraint doesn't yet document its own `.gitignore` exception), 3 reject (a
misapplied-AD claim about `jira_base_url` twice, and a companions-list suggestion inconsistent
with this repo's own sibling-spec precedent). Full detail: `## Review Triage Log` Pass 4 above.

**Verification performed:**
- `python scripts/spec_surface_check.py` — exit 0, 0 findings (was: exit 1, 1 finding).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0, 302 passed (unaffected by
  this pass; confirms the repair introduced no regression).
- `pixi run -e pyforge-steward pyforge-steward-dogfood` — exit 0 (`steward --version` +
  `steward keys audit --drift` both clean).

**Follow-up review recommendation:** false — this pass's changes are governance-metadata prose
only (no application code, no behavior change), already independently reviewed by two subagents
this pass, with all real findings either fixed inline or recorded in `deferred-work.md`.

**Residual risks:** the four deferred findings above are real but pre-existing (not introduced by
this repair) and bounded — none block the story's own Acceptance Criteria or its documented
manual live-pair verification step. The `sync.py` GitHub-URL-hardcoding defer is the most
consequential (breaks GitHub Enterprise Server routing for the new duty) but has no live-board
credentials to exercise in this environment either way.

### 2026-08-10 — Session note: work recovered from an abandoned sibling run

This story's harness re-invoked `bmad-dev-auto 8-1-bidirectional-propagation` as a fresh attempt
(`bmad-loop` run `20260810-011324-3763`, baseline `c8503d9def...`, `sprint-status-ledger.yaml`
still read `backlog`) even though this exact spec already existed with `status: done`. Investigation
found the completed, twice-reviewed implementation above was real but orphaned: it lived only on
run `20260809-231015-941e`'s branch (`bmad-loop/20260809-231015-941e/8-1-bidirectional-propagation`,
commits `b1048105be` + `4953d42742`), whose run had paused on an unrelated story's (8.2) CRITICAL
escalation and was never landed to `loop/pyforge-steward` or `main` — confirmed via
`git merge-base --is-ancestor` against both. That run's engine process was no longer running.

Rather than re-deriving this story's design and ~2,180 lines of already-reviewed implementation
from scratch, both commits were cherry-picked verbatim onto the new run's branch (now
`f070b75daf` + `4527fc02f0`, superseding the `final_revision` above) — the intervening main
history had zero file overlap with this story's changes, so both applied cleanly with no
conflicts. Re-ran full verification on the new commits: `pixi run --frozen -e pyforge-steward
pyforge-steward-test` (302 passed), `python scripts/spec_surface_check.py` (exit 0), and
`pixi run -e pyforge-steward pyforge-steward-dogfood` (clean) — all green, confirming the
recovered work is unaffected by the rebase. No design, code, or test content was altered; only
the frontmatter's `final_revision` and `review_loop_iteration` (reset to 0 per this workflow's
"done spec re-invoked" protocol, since this is a follow-up review situation, not a resumption)
were updated. Proceeding to a fresh review pass on this branch's actual commits per that protocol.

### 2026-08-10 — Final result this session: BLOCKED (real correctness defect found, not fixable
### by this session alone)

Review pass 5 (Blind Hunter, cold-context) re-confirmed a `[high][bad_spec]` defect this story's
own pass 2 had already found and pass 3 had silently dropped: the sync-point-write-after-value-
write fix from pass 1 is insufficient, because the sync-point write is itself a write that
advances the item's own `updated_at` past the value it just recorded, permanently misrouting
every reconcile past the first into the "real conflict" branch and letting AD-4's GitHub-wins
default silently overwrite a later, genuine Jira-only change. This session fixed it the way pass
2 had proposed — a `SYNC_POINT_GRACE = timedelta(seconds=30)` forward tolerance on both staleness
comparisons (commit `552381a1`, plus two new tests) — and re-verified: `pyforge-steward-test` 304
passed, `spec_surface_check.py` exit 0.

**Then review pass 6 (Blind Hunter, cold-context, reviewing pass 5's own diff) found the fix
itself does not hold.** Traced by hand and confirmed against the code: `no_op` never writes a new
sync point, and `updated_at`/`sync_point` are static server-recorded values that don't advance
with wall-clock time alone — so a genuine edit landing inside the 30s grace window is not
"deferred to the next reconcile" as claimed, it is permanently misclassified as converged, and any
*later* genuine edit still gets compared against the same stale `sync_point` and triggers the
original clobber, discarding every Jira-side change made since the last real sync. This is a
structural property, not a tuning problem: comparing an item's own aggregate `updated_at` against
a marker stored as a field on that *same* item cannot, for any grace value, distinguish "my own
bookkeeping write's self-inflicted advance" from "a coincidental genuine edit in the same window."
Full trace: `## Review Triage Log` pass 6, above.

**Why this HALTs instead of looping to another `bad_spec` repair:** the root cause traces to the
frozen `<intent-contract>`'s own literal mechanism ("compares each side's `updated_at` against its
own recorded sync point") combined with AD-2 (no sidecar store) — not to a Design-Notes-level
imprecision this session can locally amend. Three genuinely different resolutions exist (a
per-*field* rather than per-item change signal, asymmetrically available across the two vendors; a
last-synced-*value* comparison instead of a timestamp comparison, immune to this class of
self-interference but a materially different mechanism than the one the Intent names; or an
explicit, honestly-documented acceptance of a bounded data-loss window with operator-facing
telemetry distinguishing "converged" from "a change may be pending") — each a real architecture
trade-off, none obviously correct without a decision this session isn't positioned to make alone.

**Action taken:** per the intent_gap protocol, this session's three commits
(`f070b75daf`/`4527fc02f0`/`552381a1` — the recovered original implementation, the governance
repair, and the pass-5 grace-window fix) were reverted (`git reset --hard` to this branch's true
baseline `c8503d9def`) rather than left half-fixed in the worktree. **Nothing is lost**: all three
commits remain fully intact, reachable objects in this repository — the first two also still live
on `bmad-loop/20260809-231015-941e/8-1-bidirectional-propagation` (a still-existing sibling
worktree/branch), and all three are directly re-applicable by SHA once the architecture question
above is resolved. No code, tests, or `<intent-contract>` content differs from this story's true
pre-implementation baseline; every design/review artifact above (Design Notes, Spec Change Log,
Review Triage Log passes 1–6) is preserved as the record for whoever resolves this next.

**Unblock path:** a genuine architecture decision on the reconcile loop-guard's change-detection
mechanism — via `bmad-architecture` (or an equivalent operator/architect decision) against
`spec-jira-github-projects-sync/SPEC.md` and this story's own Design Notes — choosing among (or
proposing an alternative to) the three options above, then re-invoke `bmad-dev-auto` with
`8-1-bidirectional-propagation`; cherry-pick `f070b75daf`+`4527fc02f0` back in as the starting
point (still fully valid — only the reconcile loop-guard mechanism itself is in question, not the
config/client/CLI/test scaffolding around it) rather than re-deriving from scratch again.

**Residual note for the harness:** this run's `sprint-status-ledger.yaml`/`sprint-status.yaml`
still correctly read `backlog` for this story — no correction needed there. A future run
re-invoking this exact story slug should read this file's `status: draft` frontmatter (and this
section) before attempting another fresh implementation from scratch.

### 2026-08-10 — Final result this session: DONE (the contract re-issue's unblock path, executed)

**What actually happened before this session started.** Investigation (step-01/02) established
the record above was incomplete: the intent-contract had already been RE-ISSUED (frontmatter
`warnings: [contract-reissued-2026-08-10]`) from AD-5's third amendment landing in `main` via PR
#390 (`arch/steward-ad5-value-baseline`). But the "nothing landed" framing in the record above
turned out to be specific to *that* session's own three commits, not the story overall: a
**separate, independent PR (#383, `land/steward-8-1`, "recovered from the rescue tag") had
already landed the original, pre-fix `b1048105be` + governance-repair `4953d42742` snapshot into
`main`** — verified by `git merge-base --is-ancestor`, not assumed. PR #389 then correctly
identified that landed snapshot as defective (the same structural bug this file's history
already diagnoses) and downgraded `sprint-status-ledger.yaml` from `done` back to `backlog`
without reverting the code — leaving `main`, and hence this run's actual starting `HEAD`
(`c41ed99363...`), already carrying the broken `sync.py` as committed, dormant, unused code. This
run's `baseline_revision` was corrected from the stale `c8503d9def...` to reflect that reality.

**What this session did.** No cherry-pick was needed or performed (the code already existed on
this branch). Modified the already-landed `sync.py` (and its example config, docs, and three
test files) in place: replaced the timestamp-based loop guard with the amended AD-5/jira:AD-10
per-field baseline-value mechanism per the re-issued `<intent-contract>` and this file's rewritten
Design Notes. Full detail in `## Code Map` / `## Tasks & Acceptance` / `## Design Notes` above,
and the exact diff is commit `518e3747d2` (single commit, 6 files, +531/-293).

**Files changed (commit `518e3747d226c9b2920f50f070338ff875e31e5f`):**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/sync.py` — the mechanism rewrite:
  `SyncConfig`'s field rename, `baseline: dict[str, object]` replacing `updated_at`/`sync_point`,
  `_parse_baseline`/`_serialize_baseline`, `SyncBaselineTooLargeError` + the two field-size
  ceiling constants, `reconcile`'s rewritten decision logic, updated module docstring.
- `.steward/sync-config.example.yaml` — `baseline_field_id` rename + comment rewrite.
- `docs/reference/sync-jira-github-workflow-templates/README.md` — two field-provisioning
  bullets + the manual-verification step reworded for the baseline map.
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_config.py` — fixture rename.
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_duty.py` — fixture rename,
  dropped `updatedAt`/`updated`.
- `src/shared/packages/pyforge-steward/tests/conformance/test_sync_reconcile_propagation.py` —
  full rewrite: new `FakeTransport` (no timestamp fields), every case rebuilt around baseline
  JSON fixtures, one moot test deleted (`_parse_timestamp` no longer exists), 5 new cases added
  for I/O Matrix rows the old suite never covered, plus 3 more added during review (both
  identifiers given; `_parse_baseline`'s tightened falsy-value guard, 2 cases).

**Review findings (Pass 7, Blind Hunter + Edge Case Hunter, both independently ran the test
suite and `spec_surface_check.py` themselves before reporting):** 0 intent_gap, 0 bad_spec, 7
patch (all applied: `details` dict shape consistency across every return path, dry-run parity in
the true no-op summary, `_parse_baseline`'s falsy-value guard narrowed to `None`/`""` only, a
new test for the previously-uncovered both-identifiers-given branch, a bare `"status"` literal
replaced with the `_TRACKED_FIELD` constant, two docstring precision fixes), 3 defer (appended to
`deferred-work.md`: GitHub's real `text: null` field-clearing semantics unverified against a live
board; `_GITHUB_BASELINE_FIELD_CEILING`'s placeholder value unverified; a cross-side
baseline-divergence self-healing gap, refining an already-accepted non-atomicity risk that had
never actually been appended to the ledger before), 3 reject (a breaking-config-rename concern
and a legacy-value-migration concern, both moot against a feature with zero real deployments per
PR #389's own risk analysis; a speculative Jira byte-vs-character column-limit concern). Full
detail: `## Review Triage Log` Pass 7 above.

**Verification performed:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0, 308 passed (302 baseline
  + 6 net new: 8 added by this session across the mechanism rewrite and the review pass, 2
  removed as moot).
- `pixi run -e pyforge-steward pyforge-steward-dogfood` — exit 0 (`steward --version` +
  `steward keys audit --drift` both clean).
- `python scripts/spec_surface_check.py` — exit 0, no drift (all 6 changed files already governed
  by `spec-pyforge-steward`'s existing surface).
- `grep -rn "sync_point\|updated_at\|updatedAt" sync.py` — zero matches, confirming full removal
  of the retired mechanism's vocabulary from the implementation.

**Follow-up review recommendation:** false — every patch this pass was a narrow, localized,
low-to-medium-consequence fix (dict-shape consistency, a docstring, a test-coverage gap, a guard
narrowing) to a mechanism whose core design was already independently reviewed by two subagents
in the same pass and is fully covered by 308 passing tests. No architecture, security, or
data-model change beyond what Pass 7 itself already reviewed.

**Residual risks:** the three deferred findings are real but bounded and inherit this story's
own already-accepted "no live board or credentials in this environment" limitation — none block
this story's Acceptance Criteria or its documented manual live-pair verification step. The
cross-side baseline-divergence gap is the most consequential in principle (a silent, permanent
false-converged state), but it can only arise from the already-accepted, already-documented
value-write/baseline-write non-atomicity — a narrow failure window, not a routine-operation risk.

**Unblock path status: CLOSED.** The three prior sessions' commits this file's history names
(`f070b75daf`/`4527fc02f0`/`552381a1`) were never re-applied by SHA — they encoded the OLD, now
superseded timestamp mechanism (including the disproven `SYNC_POINT_GRACE` fix) and would have
required undoing as much as reusing. This session instead started from the code actually on
`main` (via PR #383) and rewrote its loop-guard mechanism directly against the re-issued
contract, which proved simpler than reconciling three divergent historical branches.
