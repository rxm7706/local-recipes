---
title: '141.1: Broker TLS is a capability, and the Story and code that build it cite it'
type: 'chore'
created: '2026-11-25'
status: 'done'
story: 141-1-broker-tls-is-a-capability-and-the-story-and-code-that-build-it-cite-it
spec: spec-pyforge-unifying-strategy
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/.memlog.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-steward-2026-07-25/prd.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
  - 'docs/foundry/capability-ledger.yaml'
  - 'src/platform/config/broker_tls.py'
  - 'src/platform/config/startup/stage_one.py'
  - 'src/platform/config/startup/__init__.py'
  - 'src/platform/config/settings/base.py'
  - 'src/platform/tests/test_broker_tls_verified.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - src/platform/config/broker_tls.py
  - src/platform/tests/test_broker_tls_verified.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-41-4-broker-tls-is-verified.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-138-1-1`. Story 41.4 made a `rediss://` broker verified rather than merely encrypted (`src/platform/config/broker_tls.py`, refused at startup by `config/startup/stage_one.py`), and `src/platform/tests/test_broker_tls_verified.py` proves it. No capability of `spec-pyforge-unifying-strategy` states it: the Spec holds it as a 2026-09-02 red-team Constraint with no stable id, Story 138.1 had to re-key Story 41.4 to that Constraint's text, and seven comments in `src/platform` still cite CAP-12 (identity roles and secret delivery).

**Approach:** Mint CAP-21 on the Spec through its memlog and an anchored render, with a `verified:` line naming the tests that prove it; register canopy:FR-52 in steward's PRD, traced from CAP-21's intent and success, with its trace-table row and a currency-reconciliation section, and re-stamp the spine; append the capability-ledger row with `pyforge steward cutover plan --append`; re-key Story 41.4's line and story spec and the seven comments; resolve the row.

Ledger key: `141-1-broker-tls-is-a-capability-and-the-story-and-code-that-build-it-cite-it`.

### Living CAP citations

- spec-pyforge-unifying-strategy CAP-21 (a broker link is authenticated, not only encrypted; minted with this story, met by Story 41.4) and canopy:FR-52 traced from it; reads the 2026-09-02 red-team Constraint and pap:CAP-6 (no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Trace CAP-21's text to the code and tests that exist, and record the trace in the Spec Change Log.
- Append the surface reconcile to the memlog of each Spec that governs a moved file before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never change a line of executable code in `src/platform`; comments and docstrings only.
- Never move another capability's text, and never touch CAP-12's genuine citations.
- Never add a flag or an architecture decision; a change that would need one stops and is reported.

## Acceptance Criteria

**Given** `DW-steward-138-1-1` reports that broker TLS (Story 41.4) is a guarantee no capability states: `spec-pyforge-unifying-strategy` holds it only as a 2026-09-02 red-team Constraint with no stable id, and seven comments in `src/platform` cite `CAP-12`, which is identity roles and secret delivery
**When** CAP-21 is minted on `spec-pyforge-unifying-strategy` through its memlog and a render, with canopy:FR-52 traced from it, and Story 41.4, its story spec and the seven comments cite CAP-21
**Then** CAP-21 states that a `rediss://` broker is verified against the configured trust and a deployed component that is not is refused at startup, its `verified:` line names `src/platform/tests/test_broker_tls_verified.py`, and no comment in `src/platform` cites CAP-12 for broker TLS
**And** no behaviour changes (comments only in `src/platform`), CAP-12's two genuine citations (`base.py`'s allauth setting and `production.py`'s IdP re-read) stay, and the row reads resolved

- **AC1 — No broker-TLS comment cites CAP-12.** Expected: exit 1 (no line matches).

  ```bash
  grep -rnE '41\.4 / CAP-12|CAP-12 / steward 41\.4' src/platform
  ```

- **AC2 — The broker's behaviour is unchanged and Platform CI's test stage holds.** Expected: exit 0.

  ```bash
  pixi run -e pyforge-guild platform-ci-local -- --test
  ```

- **AC3 — The chain holds: every requirement cites a defined capability and the ledger has the row.** Expected: exit 0.

  ```bash
  pixi run -e pyforge-guild detectors-ci
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-unifying-strategy CAP-21 (a broker link is authenticated, not only encrypted; minted with this story, met by Story 41.4) and canopy:FR-52 traced from it; reads the 2026-09-02 red-team Constraint and pap:CAP-6 (no text change); no AD moves.
- Dream: `docs/dreams/pyforge-unifying-strategy.md`, the 2026-11-25 entry (broker TLS is a capability); operator ruling of 2026-11-25: "Yes, mint it" (asked whether broker TLS should become a capability, on the recommendation that it should; the operator's own view: "i think it should be yes").
- Epic: Epic 141, minted with this story.
- Ledger key: `141-1-broker-tls-is-a-capability-and-the-story-and-code-that-build-it-cite-it`.
- Deferred-work row: `DW-steward-138-1-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."141"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the 2026-11-25 entry of `docs/dreams/pyforge-unifying-strategy.md` (broker TLS is a capability) and the operator's ruling of the same date. Not implemented.
- 2026-11-25: the trace. CAP-21's intent and success are read from `src/platform/config/broker_tls.py` (the module docstring: `CERT_REQUIRED` unless `COMPONENT_RUNTIME=local` asks by name; the operating system's trust store first, then `COMPONENT_BROKER_CA_BUNDLE`; nothing resolves over the network) and `config/startup/stage_one.py`'s `refuse_unverified_broker_tls` (three forbidden states refused by name before serving), and each clause has a test in `src/platform/tests/test_broker_tls_verified.py` (`test_production_settings_verify_a_rediss_broker`, `test_stage_one_refuses_any_policy_weaker_than_required`, `test_stage_one_refuses_an_unrecognised_policy`, `test_stage_one_refuses_a_tls_broker_with_no_trust`, `test_os_trust_store_is_consulted_before_the_explicit_bundle`, `test_plain_broker_has_no_ssl_options`, `test_local_profile_honours_cert_none`).
- 2026-11-25: session lead: AC1 found a seventh comment the minting search had missed, `src/platform/config/startup/__init__.py:19`; it is re-keyed and added to the surface, and "six" reads "seven" in the Dream entry, the Epic and this spec. AC1 exit 1 (no line matches).
