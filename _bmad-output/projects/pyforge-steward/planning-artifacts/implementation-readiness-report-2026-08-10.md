# Steward — Phase 1 backlog-truth audit (2026-08-10)

Gate report of `spec-artifact-chain-reconciliation` (CAP-2/CAP-4), the first
station audited. Method: `audit-method.md` — every verdict cites code or a
command's output. Station suite at audit time: **308 passed**
(`pixi run -e pyforge-steward pyforge-steward-test`, executed output).
Reviewed before landing by two blind lens-diverse hunters (citation-verifier
+ blind-spot hunter, no shared context); their findings changed two verdicts
and added AF-5..AF-9 — recorded inline below.

## Traceability matrix — the 4 remaining stories

| Claim | Ledger | Code reality (citation) | Verdict | Action → owner |
|---|---|---|---|---|
| 8-2 zero-loop guarantee (FR-28): N round-trips → exactly ONE propagation, demonstrated by test | backlog | Mechanism landed by 8-1: per-field baseline comparison `sync.py:762-765` + no-op path `sync.py:767-784` ("This is the zero-loop property" `:769`); single-invocation no-op test exists (`test_sync_reconcile_propagation.py:276`) but **no test invokes `reconcile` twice** — verified exhaustively: 21 call sites across 26 tests, all distinct functions. The frozen 8-1 spec explicitly defers this test to 8.2 (`spec-8-1-bidirectional-propagation.md:116-120`) | **STILL-VALID** (narrowed: the demonstration test is the deliverable) | Build as scoped. Dispatch note: the test must also cover the non-atomic baseline-refresh failure (`sync.py:869-880` — value written, baseline write fails → next tick re-propagates); a happy-path-only N-cycle test proves less than the AC claims |
| 8-3 idempotent update processing (FR-29): identical payload twice → byte-identical | backlog | Same deferral, same sentence: `spec-8-1-…md:116-120` scopes "identical-payload-twice idempotency proof" as **8.3's dedicated acceptance test**. Double-invocation idempotency falls out of the landed baseline refresh (`sync.py:849-876`). No inbound-payload *ingestion machinery* exists, by design — AD-9: "a webhook payload is never trusted as this state" (`sync.py:402`), "a webhook or schedule tick is only ever a wake-up, never a value source" (`sync.py:12-13`) | **STILL-VALID** (narrowed: the double-invocation acceptance test per the frozen spec; reviewer overturned this row's first-draft NEEDS-RESPEC — the chain had already resolved the payload framing) | build as scoped |
| 8-4 fail loud, fail alone (FR-30): a batch with one unlinked item → others complete, named error | backlog | **No batch machinery exists and no story builds it**: `reconcile()` is strictly single-pair (`sync.py:728-730`; `cli.py:231-233` makes `--github-item`/`--jira-issue` mutually exclusive); no schedule/candidate-enumeration code or story anywhere (constraint named at `epics.md:657-658`). The frozen 8-1 spec defers CAP-2/3/5 to their stories and **defers nothing for CAP-4's batch premise**. Single-pair halves exist: `SyncUnlinkedError` `sync.py:218`, tested `test_sync_reconcile_propagation.py:329,346`. Related: `SyncDuty.run` catches only `(OSError, URLError)` (`sync.py:937`) — an escaped `SyncError` exits 70 not 1, against AD-8 (bears directly on "fail loud") | **NEEDS-RESPEC** — the real dependency (batch enumeration) has no producer story | `bmad-correct-course`: add the producer story or re-scope 8-4 |
| 8-5 status-vocabulary translation (FR-31): reviewable mapping; unmapped = hard failure | backlog | The Jira direction fails hard on unmapped (`sync.py:613-616`, test `:366`) — but only because Jira's own transition list rejects it. **The GitHub direction is an unguarded raw pass-through**: `update_project_item_field` writes the raw string into a plain TEXT field, "propagated 1:1" by design (`sync.py:417-421`) — exactly the "pass-through inventing a state" the AC forbids. And the landed code cites a frozen boundary **"Never build a general status-vocabulary translation table"** (`sync.py:421-422`) that this story collides with. No mapping table in `SyncConfig` (`sync.py:97-114`) | **NEEDS-RESPEC** (reviewer overturned first-draft STILL-VALID) — scope is larger than "add the mapping" (both directions) and the boundary must be amended or the story scoped as a non-general per-config table | `bmad-correct-course` before dispatch |

## Artifact findings

| # | Finding | Evidence | Action → owner |
|---|---|---|---|
| AF-1 | Ledger epic rollup keys stale: `epic-5/6/7: backlog` with stories 2/2, 3/3, 5/5 done; `epic-8: backlog` despite 1/5 done (`in-progress` exists in the fleet vocabulary) | ledger + Tier-3 feed; cross-check 2026-08-10 | **Fixed this landing**: Tier-3 keys 5/6/7 → `done`, 8 → `in-progress`, then `sprint-ledger-sync` |
| AF-2 | epics.md `**Status:**` lines: only 15 of 33 stories carry the field (E5–E8), 10 were false; E1–E4's 18 stories cannot express status at all in the file that claims `epics_role: canonical` | grep at HEAD: 14 backlog / 1 done vs 29 done in ledger | **10 corrected this landing** (5.2, 6.1-6.3, 7.1-7.5, 8.1); systemic fix (derive or drop the field) → correct-course at steward re-plan |
| AF-3 | Epic 8 presumes machinery no story builds (schedule trigger + candidate enumeration) | `epics.md:657-658`; no producer story; frozen 8-1 spec defers nothing for the batch premise | Epic-8 preamble note **landed**; producer-story decision → `bmad-correct-course` |
| AF-4 | Stale Tier-3 `blocked` record for 8-2 predates the AD-5 amendment (blocks on the retired time-based guard) | `implementation-artifacts/bmad-dev-auto-result-8-2-zero-loop-guarantee.md` | Re-spin hazard: clear/annotate at loop-home preflight; file left untouched (true record of its moment) |
| AF-5 | **8.1's epics.md AC promises status/assignee/link + a live pair; the landed slice is status-only** — `_TRACKED_FIELD = "status"` (`sync.py:635`), assignee never propagated (`user_mapping` is a dead field: declared/validated/tested `sync.py:113,187-189` + `test_sync_config.py:46-183`, read by nothing; `.steward/sync-config.example.yaml:54-56` admits "Reserved for a future assignee-sync"), links used as join key only. Done-per-frozen-spec (which scoped the slice), but **assignee/link propagation has no owning story** | caught by the blind reviewer in the audit's own Status flip | 8.1 delivery note added to epics.md this landing; assignee/link producer decision → `bmad-correct-course` (same session as AF-3) |
| AF-6 | `test-architecture.md` wholesale stale: "3 of 18 stories done (17%)", Epics 2–4 "0 done", self-certified `[x] All 18 stories enumerated with real status` — ground truth 29/33 across 8 epics | `test-architecture.md:7,26,115,130,145,166,215-228` | Too large to hand-rewrite honestly here → `bmad-document-project` / correct-course at steward re-plan; named here so it cannot pass as current |
| AF-7 | epics.md's own inventory covers half the file: `## Epic List` (`:90-108`) stops at Epic 4; FR-19..FR-31 are cited by 13 stories and defined nowhere in the doc | `epics.md:18,90-108` vs `:575-697` | correct-course at steward re-plan (structural, not a one-line fix) |
| AF-8 | Surface docs describe a 4-duty CLI; the code has 5 (`DUTIES` incl. `sync`, `cli.py:38`) | both READMEs + `docs/dashboard/data.js:2464` contract string; also `seglabels` covers E1–E4 of 8 (editorial field — regeneration never repairs it, `generate.py:179,267`) | **Both READMEs fixed this landing**; dashboard editorial fields recorded for the marshal/board pass (Phase 2) — hand-maintained, marshal-owned surface |
| AF-9 | Sync-engine residuals carried with no DW rows: dead `user_mapping` (AF-5), unverified `_GITHUB_BASELINE_FIELD_CEILING = 1024` placeholder deciding when sync refuses (`sync.py:277-282,317-334`), `SyncDuty.run` except-clause narrower than its docstring (`sync.py:906-937`, exits 70 not 1 on escaped `SyncError`), non-atomic baseline refresh (`sync.py:869-880`) | blind-reviewer findings 12/15/16/17 | Absorb as ACs/DW rows in the Epic-8 respec (`bmad-correct-course`); deferred-work-ledger currently has zero Epic-8 entries |

## Done-claim sample — 21 of 29, all held (one narrowed)

Protocol: max(3, 20%) per epic; ACs checked cold; test-half batch-verified by
the executed suite (308 passed).

| Epic | Sampled | Key evidence |
|---|---|---|
| 1 Keys (7) | 1.2, 1.3, 1.4 | `resolve_headers` `keys.py:207` + host-gating tests `test_keys_host_scoping.py:38-81`; `encrypt_file/decrypt_file` `keys.py:413/435` + round-trip + plaintext-scan tests; `rotate_identity` `keys.py:764` + `test_keys_rotate.py`; no cron path (AC honored) |
| 2 Deploy (4) | 2.1, 2.2, 2.4 | `deploy.py` + `test_deploy_build/reconcile/dry_run/status.py` |
| 3 Provision (4) | 3.1, 3.2, 3.4 | `test_provision_env/list/verify.py`; 3.2's slice later retired by 5.1 (recorded there — supersession, not contradiction) |
| 4 Budget (3) | all | `budget.py` + `test_budget_set/show/check.py` |
| 5 Marshal seam (2) | all | Retirement real: `provision.py:17-22`, legacy wrapper GONE (`test_provision_runner.py:45`), reports `marshal init` (`:52`); ledger consumed not derived: `deploy.py:262-264` (AD-71 banner) |
| 6 Modules (3) | all | `test_provision_module.py:146-261` incl. named failures (6.3); `test_provision_list_modules.py` |
| 7 Container (5) | 7.3, 7.4, 7.5 | secrets-scan gate `Containerfile:122-152` (7.3 + 7.5 build-time proof); `VOLUME` triple `Containerfile:216` (7.4) |
| 8 Sync (1) | 8.1 | `reconcile()` `sync.py:713` + 26 propagation tests; landed `553ecc9e79` (PR #397, merge `e3155a32e7`). **Held as narrowed**: done per its frozen spec's status-only slice — see AF-5 for the un-owned remainder |

Not sampled (8 of 29): 1.1, 1.5, 1.6, 1.7, 2.3, 3.3, 7.1, 7.2 — no adverse
signal from neighbors; their test files exist in the green suite.

## TEA / coverage-debt

| Epic | AC | Covering test | Status |
|---|---|---|---|
| 8 | 8.1 "demonstrated against a **live pair**" | fake-transport conformance tests only (all 26 inject a fake transport) | **coverage-debt** — live-pair demonstration not evidenced in-repo; non-gating, operator disposes |
| 8 | 8.1 assignee/link propagation | none — feature absent (AF-5) | not coverage-debt: nothing to cover; a producer-story decision |
| 1–7 | all sampled ACs | dedicated conformance file per story (see sample table) | covered |

## Verdict

Steward's backlog: **8-2 and 8-3 dispatch as-is** (both narrowed to their
demonstration tests, exactly as the frozen 8-1 spec sequenced); **8-4 and 8-5
need `bmad-correct-course` before dispatch** (missing batch-producer story;
mapping-vs-frozen-boundary collision + both-directions scope). The 21 sampled
done-claims held — one (8.1) narrowed by the blind review to
done-per-frozen-spec with an un-owned assignee/link remainder (AF-5). The
chain carried nine artifact findings: AF-1/AF-2/AF-3/AF-8 fixed or noted this
landing, AF-4 deferred to re-spin preflight, AF-5/AF-6/AF-7/AF-9 routed to
one `bmad-correct-course` session at steward re-plan. Steward's ledger tells
the truth about what is done; its prose surfaces (epics.md inventory,
test-architecture.md, READMEs) had drifted well behind it.
