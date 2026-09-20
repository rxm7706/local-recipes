---
title: '61.4: Signed outbound slice'
type: 'feature'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
baseline_revision: 'ff2455866b3379fccf333e175e5166dab351c67e'
---

<intent-contract>

## Intent

**Problem:** A dump of Jira or factory BMAD can leave unsigned.

**Approach:** Default deny; a named slice plus recorded signer is required. The vendor loads our file — we do not PAT into their org.

## Boundaries & Constraints

**Always:**
- Default deny.
- Named slice plus recorded signer required.

**Never:**
- Do not PAT into the vendor private GitHub.
- Do not treat Epic 8 as this product.
- Do not flip any Epic 44 blocked key.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| unsigned dump | no signer | refused | refuse |

</intent-contract>

## Binding

Parent Spec capability: `spec-work-passports-dated-extracts CAP-4`.
Surface: outbound loader; named outbound-signer role on the existing app..
Ledger key: `61-4-signed-outbound-slice`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-61-4-signed-outbound-slice.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding added 2026-09-19).

## Review Triage Log

### 2026-09-20 — Review pass
- verdicts: 15 findings — high 0, medium 2, low 7, false 6, maybe-false 0
- findings:
  - `[low]` `[patch]` `load_extract` does not zero `slice_name`/`signer` for non-outbound directions, contradicting the module/model docstrings' claim they are "ignored entirely" / always blank for inbound — applied: added `if direction != "outbound": slice_name = ""; signer = ""` right after the direction check, before either value is used anywhere.
  - `[medium]` `[patch]` outbound gate checks `.strip()` for blankness but then persists the raw, un-stripped `slice_name`/`signer` to `record_corridor_load` — a whitespace-padded value (e.g. `" operator "`) passes the gate but is stored padded, undermining exact-match audit search/dedup on the very field the story exists to make trustworthy — applied: the gate now reassigns `slice_name = (slice_name or "").strip()` / `signer = (signer or "").strip()` before the blankness checks, so the stripped values are what get validated, persisted, and returned.
  - `[low]` `[patch]` `test_load_extract_outbound_without_slice_name_raises`'s docstring claims the error is "raised before the dashboard extra ... are ever consulted," but the dashboard-extra check and idempotency probe actually run before the gate — only the transport-declared check runs after it — applied: corrected the docstring to state the real ordering.
  - `[low]` `[patch]` whitespace-only rejection tested asymmetrically: `slice_name` is only tested with `""`, `signer` only with `"   "` — a regression dropping `.strip()` from either specific check would go uncaught — applied: added `test_load_extract_outbound_with_whitespace_only_slice_name_raises` and `test_load_extract_outbound_with_blank_signer_raises`.
  - `[low]` `[reject]` no over-length test for the new `slice_name`(128)/`signer`(255) `CharField`s mirroring the existing waybill-length test — rejected: unlikely to be hit in everyday CLI use, the generic `DataError` handling already covers overflow the same way it does for every other field on this model, and no such per-field convention is consistently enforced elsewhere (e.g. `transport` has none either).
  - `[low]` `[patch]` CLI outbound summary text (`slice={x} signer={y}`) has no delimiter/quoting, so a slice/signer value containing a space renders ambiguously (JSON payload unaffected) — applied: changed to `f' slice="{outcome.slice_name}" signer="{outcome.signer}"'` and updated the one dependent assertion.
  - `[low]` `[reject]` `slice_name`/`signer` added to admin `search_fields` with no `db_index`, unlike `direction`/`batch_sha`/`waybill` — rejected: no demonstrated current need, would require a new migration for a speculative future-scale optimization.
  - `[low]` `[reject]` doubled trailing period typo in this spec's own Binding line ("the existing app..") — rejected per the standing rule that any finding whose fix is to edit this build's spec is rejected; also pre-existing and untouched by this diff.
  - `[medium]` `[patch]` edge-case-hunter independently found the same whitespace-padding-persisted defect as the row above — same group, same fix, shares the route — applied (see above).
  - `[false]` `[reject]` intent-alignment: `sprint_ledger_query.py`'s `jira-csv`/`github-json`/`static-dossier` exporters are a literal-match surface for "a dump of Jira" left untouched — refuted: this spec's own Binding section states "Surface: outbound loader," explicitly pinning the corridor-load duty as the intended surface, not the ledger-query exporters.
  - `[false]` `[reject]` intent-alignment: the gate has no coupling to an actual outbound file transfer — refuted: the intent's own "Never: Do not PAT into the vendor private GitHub" boundary rules out any push-based transfer being in scope at all, so there is nothing else to couple to.
  - `[false]` `[reject]` intent-alignment: "named slice" is unvalidated free text with no declared catalog, unlike the parallel transport check — refuted: the Approach text only requires "a named slice," and the Matrix's sole row never tests an unknown-slice scenario, so "any non-blank label" is the plain reading.
  - `[false]` `[reject]` intent-alignment: "recorded signer" is unauthenticated, a presence check only — refuted: the owning Dream's operator ruling 5 ("Default: the steward operator running Drop Night") establishes v1 records identity without authenticating against a roster; this is the governing ruling, not a gap.
  - `[false]` `[reject]` intent-alignment: the "we do not PAT into their org" boundary is satisfied only by omission, with no explicit test asserting the absence of new credential code — refuted: independently verified (grep + trace) that no new outbound network/credential/PAT code exists anywhere in the diff.
  - `[false]` `[reject]` intent-alignment: the diff's default-deny also covers "no slice" in addition to the Matrix's sole "no signer" row — not a defect; broader coverage than the single specified row is not a bad outcome.

## Auto Run Result

**Summary:** `steward load outbound` (Story 61.1) now default-denies unless the caller supplies both a named `--slice` and a recorded `--signer`; both are persisted on the existing `CorridorLoad` row and read back verbatim on an idempotent repeat, never re-validated or re-signed. `inbound` loads are unaffected. No new outbound transport or vendor-side authentication was added — this reuses the same declared `corridor.yaml` transports as inbound, per the "the vendor loads our file — we do not PAT into their org" boundary.

**Files changed:**
- `src/shared/packages/pyforge-steward/src/pyforge/steward/corridor.py` — `load_extract` gains the outbound default-deny gate (`slice_name`/`signer` required, non-outbound directions normalized to blank, values stripped before validation/persistence); `LoadDuty` threads `--slice`/`--signer` through and quotes them in the CLI summary; `SIGNER_ROLE` constant added.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `--slice`/`--signer` added to the `load outbound` subparser only, defaulting to `""` (a missing one is a duty-level refusal, not a usage error).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/models.py` — `CorridorLoad` gains blank-default `slice_name`/`signer` fields.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/migrations/0005_corridorload_signer_corridorload_slice_name.py` — new migration for the two fields.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/corridor_load.py` — `record_corridor_load` persists/returns `slice_name`/`signer` on every branch, reading back the originally recorded values on an idempotent hit.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/admin.py` — `CorridorLoadAdmin` surfaces the two new fields in `list_display`/`search_fields`.
- `src/shared/packages/pyforge-steward/tests/unit/test_corridor.py` — new coverage for the gate (missing slice, missing signer, whitespace-only variants of both, happy path, idempotent-repeat preserves original signer/slice, inbound unaffected) plus updated pre-existing tests.

**Review findings breakdown** (full detail in the Review Triage Log above, pass dated 2026-09-20):
- **Patched (5 entries, applied and re-verified):** `load_extract` now zeros `slice_name`/`signer` for non-outbound directions; the gate strips both values before validating/persisting them (closes a whitespace-padding-bypasses-audit-fidelity defect independently found by two review layers); a misleading test docstring about check ordering was corrected; two missing whitespace-only test cases were added; the CLI summary now quotes `slice=`/`signer=` values.
- **Deferred:** none — every non-patched finding was rejected outright (below), not deferred.
- **Rejected (7 findings):** no over-length test for the new `CharField`s (unlikely to be hit, generic `DataError` handling already covers it, no such convention is universal in this model); missing `db_index` on the two new admin-searchable fields (no demonstrated need, would need a speculative new migration); a doubled-period typo in this spec's own Binding line (fixing it would mean editing this build's spec, which is rejected by standing rule, and it predates this diff); four intent-alignment divergence claims (jira-csv/github-json/static-dossier exporters as an alternate "unsigned dump" surface; the gate's lack of coupling to an actual file transfer; the unvalidated free-text slice name; the unauthenticated signer) refuted respectively by this spec's own Binding section ("Surface: outbound loader"), the intent's own "no PAT into vendor org" boundary, the Approach text's plain wording, and the owning Dream's operator ruling 5; plus one claim that broader-than-specified test coverage is itself a problem (it is not).

**Follow-up review recommendation:** `false`. This pass patched one `medium` entry and four `low` entries — no `high`, and fewer than two `medium` — so per the first-pass threshold this has converged.

**Verification performed:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` (the spec's declared verify command), read via exit code: pass 1 (pre-patch) `0`, 1552 passed/4 skipped; pass 2 (post-patch) `0`, 1554 passed/4 skipped.
- Matrix Test Audit: the I/O matrix's sole row ("unsigned dump / no signer / refused") is covered by `test_load_extract_outbound_without_signer_raises` and `test_load_duty_outbound_without_signer_fails`, both of which ran and passed in both verification passes.
- Full diff traced end-to-end by two independent review layers (edge-case-hunter, verification-gap) with no unresolved verification gaps reported.

**Residual risks:** none rated `high`/`medium` and unresolved. The rejected items above (no dedicated over-length test, no DB index on the two new searchable fields) are named, low-severity, and speculative rather than demonstrated.

