---
title: "84.3: Trusted ingress addresses are IP networks"
type: 'fix'
created: '2026-10-03'
status: 'done'
followup_review_recommended: false
baseline_revision: '861bf2bcc15d71702693a58dabada103df411cb9'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `TrustedIngress.addresses` accepts strings that can never match (hostnames, CIDR blocks compared as strings), so a mis-declared ingress silently trusts nothing or the wrong peer.

**Approach:** Parse each address with `ipaddress.ip_network` (a bare IP is a one-address network), fail construction on a hostname or malformed value, and match the peer by network membership with IPv4-mapped IPv6 normalized.

Ledger key: `84-3-trusted-ingress-addresses-are-ip-networks`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- The steward capabilities that shipped each behaviour (Epic 9's audit trail, Story 9.1's ingress); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a CIDR block When a peer inside it connects Then it is trusted
- Given a hostname When TrustedIngress is built Then construction fails naming it
- Given an IPv4-mapped IPv6 peer When it matches a declared IPv4 network Then it is trusted
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-9-1-9` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Keep the error at startup, not per request. Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix.

**Never:** Never resolve a hostname at runtime.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phase 3)

- `DW-FU-9-1-9` — Validate ingress addresses: TrustedIngress parses each address with ipaddress.ip_network (a bare IP counts as a one-address network), so a hostname or malformed value fails at construction; the middleware matches the peer by network membership after unwrapping an IPv4-mapped IPv6 address.

## Binding

Parent: The steward capabilities that shipped each behaviour (Epic 9's audit trail, Story 9.1's ingress)
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-03 (Phase 3) entry.
Ledger key: `84-3-trusted-ingress-addresses-are-ip-networks`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 3 rulings (rulings page `rulings` collection; "group them by module, as Phase 2 did").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-03 — Landing review (operator session) — landed by hand
- The fix holds: addresses parse as IP networks at construction, an IPv4-mapped IPv6 peer is unwrapped before the membership test, and a peer that does not parse is refused.
- `medium` `patch` (applied by the operator session) `ipaddress.ip_network(address, strict=False)` masked host bits, so `192.168.1.10/16` was accepted as `192.168.0.0/16`: a typo on the trust perimeter silently trusted 65,536 peers. Parsing is now strict and the error names the case; `test_trusted_ingress_rejects_a_cidr_with_host_bits_set` holds it (it fails with `strict=False`).


### 2026-10-03 — Review pass
- verdicts: 8 findings — high 0, medium 2, low 1, false 2, maybe-false 0, reject 3
- findings:
  - `[medium]` `[patch]` CIDR ingress lacked an out-of-range peer refusal test — added `test_untrusted_peer_outside_a_declared_cidr_is_refused` in test_dashboard_middleware.py.
  - `[medium]` `[patch]` IPv4-mapped literal declarations did not match IPv4 peers — collapse /128 `::ffff:` networks to IPv4 in declarations.py __post_init__; construction test added.
  - `[low]` `[patch]` TrustedIngress docstring still described string peer lists — updated addresses docstring for IP-network semantics.
  - `[false]` `[reject]` Verification-gap defer for mapped-peer inside CIDR — shared unwrap path already covered by existing tests after CIDR patch.
  - `[false]` `[reject]` Blind Hunter docstring-only finding after patch applied.
  - `[reject]` `[reject]` Stale test docstring on bare-string addresses — cosmetic; left unchanged (not worth churn).
  - `[reject]` `[reject]` Missing malformed-octet construction test — hostname test plus ip_network loop sufficient.
  - `[patch]` `[patch]` Deferred-work ledger DW-FU-9-1-9 closure — updated deferred-work-ledger.md with resolution and verified path:line cites.

## Auto Run Result

Status: done

**Summary:** TrustedIngress now parses each address as an IP network at construction (hostnames fail with a named error). DashboardIdentityMiddleware trusts peers by network membership, unwrapping IPv4-mapped IPv6 peers and collapsing /128 mapped literal declarations to IPv4 networks. Closed DW-FU-9-1-9 in the deferred-work ledger.

**Files changed:**
- src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/declarations.py — parse `_networks`, validate FORM, mapped-literal collapse
- src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/middleware.py — `_peer_in_trusted_ingress`
- src/shared/packages/pyforge-steward/tests/unit/test_dashboard_declarations.py — hostname rejection, CIDR/mapped construction tests
- src/shared/packages/pyforge-steward/tests/unit/test_dashboard_middleware.py — CIDR in/out, IPv4-mapped peer tests; refusal message uses IPs only
- _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md — DW-FU-9-1-9 resolved
- _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md — surface reconcile entry

**Review:** 3 patches applied (2 medium, 1 low); 3 rejected as cosmetic or redundant; 2 false.

**Verification:** `pixi run --frozen -e pyforge-steward pyforge-steward-test` pass; `pixi run --frozen -e pyforge-guild lint-types` pass; `python scripts/spec_surface_reconcile.py` OK.

**Residual risks:** AD-4 still depends on `scope["client"]` reporting (documented precondition); comma-folded duplicate headers remain on the ledger separately.
