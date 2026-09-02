# Steward — red-team CRITICALs readiness (2026-09-02)

Gate of `spec-pyforge-unifying-strategy` Epic 40 after the 2026-09-02
adversarial review found two shipped CRITICALs (X-1 unverified mint root,
S-1 volatile unbounded broker) and the operator chose option 1: land them
as two steward stories before anything else dispatches on this chain.

**Question:** could a developer implement 40.1 and 40.2 without inventing
decisions?

**Verdict: READY — proceed.**

Both stories are additive over shipped code, cite the exact lines they
change, reuse settings and dependencies already present (`OIDC_*`,
`pyjwt`, `cryptography`, `redis-server` in `platform-dev`), and name what
they must not do. No AD or FR changes. No packaging gate.

## Concerns (do not invent; do not block)

| Concern | Where | Why it does not block |
|---|---|---|
| Existing test encodes the X-1 hole (`_idp_bearer()` fake `.sig`) | `test_django_pyforge_assertion.py:96` | 40.1 AC names the flip explicitly; the old fixture becomes the refusal test |
| Two chart invariants assert broker `emptyDir` | `test_chart_invariants.py:1164,1709` | 40.2 AC re-scopes them to cache; a story that keeps them green unchanged has not done the work |
| `MemoryRedis` has no TTL / restart | `django_pyforge/events/memory.py` | 40.2 requires the durability proof on a real `redis-server`; skip-if-absent must be loud |
| Roles are bare station names (X-3) | `django_pyforge/roles.py` | 40.1's station-in-roles check works today and survives R-13's prefixes if routed through `roles.py` |
| Bus retry / Celery ack semantics still weak (A-2, S-2) | review R-9 / R-10 | Explicitly `deferred:` on 40.2 so a green 40.2 is not read as "the bus is resilient" |
| Operator yes/no on drafts | SCP § 2 item 6.3 | Drafted under direction; approval owed before `bmad-build` |

## Trace

| Intent | Story | Spec |
|---|---|---|
| CAP-6 / AD-7 root is IdP-verified | 40.1 | `spec-40-1-idp-bearer-is-verified-before-mint.md` |
| CAP-11 / AD-10 broker loses nothing on restart; CAP-8 / AD-8 DLQ and applied keys survive | 40.2 | `spec-40-2-redis-broker-is-durable-and-bounded.md` |

## Dispatch order

1. `bmad-build` + `spec-40-1-idp-bearer-is-verified-before-mint.md` (exploitable first)
2. `bmad-build` + `spec-40-2-redis-broker-is-durable-and-bounded.md` (may run in parallel; disjoint files)
3. Then a second `bmad-correct-course` for the review's HIGH set (R-4 … R-16)

`BMAD_ACTIVE_PROJECT=pyforge-steward`. Physical paths only. Neither story
starts cutover Phase 1; both gate it.
