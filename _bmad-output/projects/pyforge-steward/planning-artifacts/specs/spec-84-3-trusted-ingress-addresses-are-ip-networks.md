---
title: "84.3: Trusted ingress addresses are IP networks"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
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

- No review has run yet.
