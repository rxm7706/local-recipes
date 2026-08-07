<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-07 -->
---
title: 'Story 1.7: Retiring a credential leaves a record, not a silent gap'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Steward has no way to record "this credential should no longer be trusted" when it has no upstream API to actually revoke it itself (most of the time — an observed, pre-existing credential like a `GITHUB_TOKEN`-class entry). Today that fact would live nowhere: not the inventory, not anywhere an operator would think to check later.

**Approach:** Add `keys.py`'s `revoke_identity`, marking the currently-`active` inventory entry for a `--scope` `status: retired` and returning it — a pure local bookkeeping write via Story 1.4's `load_inventory`/`save_inventory`, no cryptographic operation and no network call of any kind. Unlike `rotate_identity` (Story 1.4), `revoke_identity` works on BOTH `issued` and `observed` provenance, since it never touches an `age` identity's actual decrypt capability — there is no re-encryption to gate on provenance. `KeysDuty` prints provenance-appropriate remediation guidance alongside the retirement: for an `issued` entry, an explicit warning that the identity file itself can STILL decrypt its secrets (revoke ≠ rotate — this command changes Steward's record, not `age`'s cryptography) and a pointer to `keys rotate` if that needs to change; for an `observed` entry, guidance to revoke at the credential's own origin, with the literal JFrog wording the epic's own historical incident calls for when the scope name says so.

## Boundaries & Constraints

**Always:**
- `revoke_identity` finds the entry with `status == "active"` for `scope` (either `provenance`) — else `InventoryError`, never a crash.
- `revoke_identity` writes exactly one field change (`status: "active"` → `"retired"`) to the matched entry; every other field (`name`, `scope`, `provenance`, `last_rotated`, `identity_path`, `secrets`) is carried over unchanged — revoke is a record-only action, never a rewrite of history.
- `KeysDuty`'s `revoke` verb prints a remediation message keyed on the retired entry's `provenance` (`issued` vs `observed`); an entry whose `scope` names a recognized provider (currently: `jfrog`) gets that provider's literal remediation wording (the epic's own named historical incident), matching this story's own AC example verbatim.
- No third-party provider API client import anywhere in this module or story's new code — `requests`/`httpx`/`github`/`gitlab`/provider-SDK imports are all absent, enforced by a dedicated meta test (this story's own second AC, made a regression test rather than left as a code-review claim).
- No network call anywhere in `revoke_identity` or the `revoke` verb — pure filesystem read/write via the existing `load_inventory`/`save_inventory`.
- `KeysDuty.run` catches `ValueError` (covers `InventoryError`) from `revoke_identity` as a duty-level failure (`EXIT_FAILED`), matching `rotate`'s existing boundary.

**Block If:** none — self-contained CLI + library work, no ambiguous external decision points.

**Never:**
- No re-encryption, no `age`/`age-keygen` subprocess call anywhere in `revoke_identity` — that is `rotate_identity`'s (Story 1.4) job; revoke is deliberately a cheaper, purely-local action, and the remediation text for an `issued` entry says so explicitly rather than implying the secrets are now protected.
- No deletion of the retired entry, no removal from the inventory — it stays visible via `steward keys list` (Story 1.5) with `status: retired`, exactly the "leaves a record" the story's title asserts.
- No calling any provider's actual revocation endpoint for ANY provenance, `issued` or `observed` — this story's v1 non-goal, per the PRD.
- No new inventory schema fields — `revoke` reuses `KeyIdentityEntry` exactly as Story 1.4 defined it.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Revoke an `issued`/`active` entry | An `issued` entry, `status: active` | Entry flips to `status: retired`, all other fields unchanged; remediation text warns the identity file can still decrypt its secrets and points at `keys rotate` | No error expected |
| Revoke an `observed`/`active` entry, generic scope | An `observed` entry, `status: active`, scope not a recognized provider name | Entry retired; remediation text is the generic "revoke at its own origin" guidance | No error expected |
| Revoke an `observed`/`active` entry, `scope` names JFrog | An `observed` entry, `scope="jfrog"` (or containing "jfrog") | Entry retired; remediation text is the literal JFrog-specific wording | No error expected |
| Revoke a `retired` entry (already revoked) | No `active` entry exists for `scope` (all retired) | Refused — no double-retirement, no silent no-op | `InventoryError` / `DutyResult(ok=False)` |
| Revoke an unknown scope | No entry at all for `scope` | Refused | `InventoryError` / `DutyResult(ok=False)` |
| Retired entry visible in `keys list` | After a successful revoke | `steward keys list` shows the entry with `status: retired` | No error expected |
| No provider API client imported | This story's code inspected | No `requests`/`httpx`/provider-SDK import anywhere in the package | Meta test, not a runtime path |
| No network call | This story's code inspected/executed | `revoke_identity` performs only local file I/O | No error expected — proven by the same tmp_path-only test fixtures every other story uses |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` -- add `revoke_identity`, `_PROVENANCE_REMEDIATION`, `_SCOPE_SPECIFIC_REMEDIATION`, `_remediation_for`, and the `revoke` verb on `KeysDuty`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- add `keys revoke --scope <name> [--inventory <path>]` subparser; extend `_KEYS_VERBS`/`_HELP["keys"]`
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_revoke.py` -- NEW: covers the I/O matrix, both at the primitive and CLI level
- `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` -- add `test_no_third_party_provider_api_client_imported` (this story's own second AC)

## Tasks & Acceptance

**Execution:**
- [x] `keys.py` -- add `revoke_identity(inventory_path, *, scope) -> KeyIdentityEntry` -- finds the `active` entry for `scope` (any provenance), flips `status` to `retired`, `save_inventory`s the result
- [x] `keys.py` -- add `_PROVENANCE_REMEDIATION` (keyed `"issued"`/`"observed"`) and `_SCOPE_SPECIFIC_REMEDIATION` (keyed by a lowercase substring of `scope`, currently `"jfrog"`), and `_remediation_for(entry) -> str` -- scope-specific wins over provenance-generic
- [x] `keys.py` -- extend `KeysDuty`'s `_KEYS_VERBS`/`run` with `revoke`, catching `ValueError` the same way `rotate` does; summary includes both the retirement confirmation and the remediation text
- [x] `cli.py` -- add `keys revoke --scope <name> [--inventory <path>]` subparser
- [x] `tests/conformance/test_keys_revoke.py` -- cover every I/O matrix row
- [x] `tests/meta/test_invariants.py` -- `test_no_third_party_provider_api_client_imported`

**Acceptance Criteria:**
- Given an identity present in `.steward/keys-inventory.yaml`, when `steward keys revoke --scope <name>` is run, then the inventory entry is marked retired (visible in a subsequent `steward keys list`), and stdout prints the manual remediation steps appropriate to that identity's provenance (e.g. "rotate the upstream JFrog token; this tool cannot call JFrog's revocation API" for an `observed` JFrog entry).
- Given no third-party provider credentials or network calls exist in this story's implementation, when the code is reviewed, then no JFrog/GitHub/Anthropic API client import exists — revoke is a local record-and-guide action only.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (adversarial re-read of the diff before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 1
- defer: 0
- reject: 0
- addressed_findings:
  - `[medium]` `[patch]` The first draft's `issued`-provenance remediation text said only that the identity "can still decrypt its secrets" without naming the concrete follow-up action clearly enough (it referenced "rotate" in prose but not the exact command) — an operator acting on this message under incident pressure should not have to go find the right invocation. Reworded to include the literal `steward keys rotate --scope <scope>` command with the entry's own scope substituted in, mirroring how the JFrog-specific text names an exact action rather than a vague pointer.
  - Verified by execution that `revoke_identity` never imports or calls anything network-shaped: grepped the diff for `import` statements and confirmed the only new imports are none (revoke reuses `load_inventory`/`save_inventory`/`KeyIdentityEntry`, already imported); `test_no_third_party_provider_api_client_imported` passes against the actual module.

## Design Notes

**Why revoke works on BOTH `issued` and `observed` provenance, unlike rotate:** `rotate_identity` (Story 1.4) is gated to `issued` only because it performs a real cryptographic operation (re-encrypting secrets to a NEW identity) that only makes sense for an identity Steward itself minted and controls the secret-key file location for. `revoke_identity` performs no cryptographic operation at all — it only flips a bookkeeping field — so there is no operation to gate by provenance. This is also *why* the `issued`-provenance remediation text has to be so explicit: an operator revoking an `issued` identity might reasonably (and wrongly) assume "revoked" means "can no longer decrypt," which is only true after a `keys rotate`.

**Why JFrog gets literal, hardcoded remediation text but nothing else does:** this story's own AC (epics-with-stories.md) gives the JFrog wording as a literal example, and JFrog is one of the two named historical incidents motivating this whole epic (`docs/dreams`/PRD) — so honoring the example exactly, keyed by a scope-name substring match, both satisfies the AC literally and costs nothing (a plain string-keyed dict, no provider SDK, no network). Adding entries for other named providers (GitHub, Anthropic) was considered and rejected: neither is named as a *scope example* anywhere in this epic's specs, and inventing wording for a provider nobody asked about would be speculative surface ahead of any story that names it.

**Why an already-retired scope is refused rather than a silent no-op:** the story's own title is "leaves a record, not a silent gap" — a second `revoke` on an already-retired scope succeeding silently would itself be a small silent gap (did it do anything? which retirement does the printed remediation now refer to?). Refusing with a clear `InventoryError` (mirrors `rotate_identity`'s identical precedent for an already-retired scope) keeps the operator's mental model of "what state is this credential in" always backed by an explicit answer.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: all tests pass (Stories 1.1-1.6's existing suite + this story's new tests)
- `pixi run -e pyforge-steward steward keys revoke --help` -- expected: shows `--scope`/`--inventory`

**Results (2026-08-07):**
- `pixi run -e pyforge-steward pyforge-steward-test` — 96 passed, 0 failed (full Epic 1 suite: Stories 1.1-1.7 combined, unit + conformance + meta).
- `pixi run -e pyforge-steward pyforge-steward-dogfood` — exits 0 (`steward --version` then `steward keys audit --drift`, both clean against this repo's live state).
- `pixi run -e pyforge-steward steward --version` / `steward --help` — unchanged (`steward 0.1.0`; `keys/deploy/provision/budget` still the only four duties).
- `pixi run -e pyforge-steward steward keys revoke --help` — shows `--scope`/`--inventory` as expected.
- `ruff check` on every file this story (and 1.4-1.6) touched: only pre-existing Stories-1.1/1.2/1.3 findings remain (the `cli.py` `Sequence` import, `keys.py`'s `_http` `noqa: E402`, `test_invariants.py`'s nested `tomli` import) — zero new findings introduced across all four stories.

This closes Epic 1 (Keys — Credential Lifecycle): all 7 stories done (1.1-1.7). Per this session's own instructions, `epic-1` is flipped to `done` in `sprint-status.yaml` now that all four remaining stories (1.4-1.7) are complete.

</intent-contract>
