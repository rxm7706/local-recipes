---
title: Sprint Change Proposal — red-team CRITICALs (verified mint, durable broker)
date: 2026-09-02
project: pyforge-steward
chain: spec-pyforge-unifying-strategy
status: approved — operator 2026-09-02: "approve steward Epics 40 through 43 and Mason Epic 13"
trigger: Red-team architecture review (research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md) — X-1 / R-1 and S-1 / R-2
mode: batch
scope: minor
operator: Rxm7706
---

# Sprint Change Proposal — red-team CRITICALs (CAP-6 mint, CAP-11 broker)

## 1. Issue summary

The 2026-09-02 adversarial review of `docs/dreams/pyforge-unifying-strategy.md`
cross-checked the Dream against shipped code and found two CRITICALs that the
living chain already claims closed:

- **X-1 (CAP-6 / AD-7 / RFC-3).** `POST /assertion/mint/` decodes the caller's
  IdP bearer and trusts `sub`/`groups` **without verifying signature, issuer,
  audience or expiry** (`django_pyforge/assertion/identity.py`). The test
  suite encodes it: `_idp_bearer()` fabricates `header.payload.sig` and the
  host mints from it. Every downstream gate (supervisor `start`, Lane 3 row
  slicing, MCP tool leasing) trusts the result. The module docstring says
  "Live token-exchange is deferred"; the deferral shipped as the live path.
- **S-1 / A-3 (CAP-11 / AD-10 / RFC-2, CAP-8 / AD-8).** `redis-broker` is
  `noeviction` **without `maxmemory`** (unlimited), on `emptyDir`, unlimited
  resources, and it carries Celery queue + results, Channels, the event
  stream, the PEL, the DLQ and the idempotency keys. One restart loses all
  of them; unbounded growth OOM-kills it first.

Neither is "genuinely unbuilt" work the chain forgot; both are shipped work
whose success clause was read too narrowly. This proposal is not a re-open of
the review's HIGH findings — those route through a later correct-course once
these two land.

## 2. Change-navigation checklist (recorded)

| # | Item | Status | Finding |
|---|---|---|---|
| 1.1 | Triggering story | Done | Not one story. Root causes: **19.x / 21.x** (assertion + mint, `django-pyforge`), **12.6** (Redis hardened, still ephemeral), **24.x** (CloudEvents fabric). Trigger is the red-team research file, not a dev session. |
| 1.2 | Problem type | Done | *Misunderstanding of original requirements* (CAP-6 "independently verify" was satisfied for the assertion, not its root; CAP-11 was satisfied by separation, not durability) plus *technical limitation* (`maxmemory 0` = unlimited). |
| 1.3 | Evidence | Done | File:line citations in the review's evidence index; both reproduced by reading code, not inferred. |
| 2.1 | Current epic completable | Done | Epics 18–39 stay `done`; none is reopened. The fixes are additive. |
| 2.2 | Epic-level change | Done | **Add Epic 40** (two stories). Not a modify of 19/21/12/24 — those ledgers are archaeology; a new epic keeps the audit trail honest. |
| 2.3 | Remaining epics | Done | 39.4 (pixi feature bundle) unaffected. No other backlog on this chain. |
| 2.4 | New epics needed | Done | Yes: Epic 40. The review's HIGH set (R-4…R-16) is **not** minted here — one CRITICAL epic first, then a second correct-course. |
| 2.5 | Priority / order | Done | Epic 40 dispatches **before** any further story on this chain and before cutover Phase 1 (`python-foundry`). 40.1 and 40.2 are independent (different files) and may run in parallel. |
| 3.1 | PRD conflicts | Done | No FR changes. FR-30 wording holds; its *consequence* gains one testable line (broker restart loses nothing). FR-31/CAP-12 intent is what 40.1 restores. PRD § 14 gets a dated paragraph. MVP unaffected. |
| 3.2 | Architecture conflicts | Done | No AD changes. AD-7 already requires an IdP-verified root; AD-10 already says broker does not evict; AD-15 requires a per-invariant test. Both stories are AD-compliant implementations. |
| 3.3 | UI/UX | N/A | No portal surface changes. |
| 3.4 | Other artifacts | Action-needed | Helm chart, values, `deploy/README.md`, `cluster-bringup.md`, `resilience-invariants.md` RFC-2/RFC-3 rows, sibling `spec-local-ocp-hybrid-environment` CAP-3 (broker supersession), Dream sizing table, two chart invariant tests re-scoped. All named in the story specs. |
| 4.1 | Direct adjustment | Viable | Two stories, effort **M** each, risk **Low** (both are additive; the only behavior change is a fake bearer now refused and a broker that persists). |
| 4.2 | Rollback | Not viable | Nothing to revert; the shipped code is the baseline both stories build on. |
| 4.3 | MVP review | Not viable | Scope is not the problem; correctness is. |
| 4.4 | Selected path | Done | **Option 1 — Direct Adjustment**, operator-chosen. |
| 5.x | Proposal components | Done | Sections 3–5 below. |
| 6.3 | Explicit approval | Done | Operator 2026-09-02: "approve steward Epics 40 through 43 and Mason Epic 13". |
| 6.4 | Ledger | Done | `40-1-…`, `40-2-…` = `backlog`; `epic-40` = `backlog`; `epic-40-retrospective` = `optional`. Hand-inserted in the tracked twin (Tier-3 feed absent in this clone); `sprint-ledger-sync` is monotonic and will not regress them. |

## 3. Recommended approach

**Direct Adjustment.** New **Epic 40 — Red-team CRITICALs: verified mint,
durable broker**, two stories, both `ready-for-dev`, both **deps: none**,
parallel-safe (40.1 touches `django_pyforge/assertion/*`, settings, stage-1;
40.2 touches the chart, `base.py` Celery block, `events/*`). Dispatch order is
operator's choice; recommended 40.1 first because it is the exploitable one.

**Rationale.** The alternative (fold each fix into the story that shipped the
gap) would edit `done` ledgers and hide that a CRITICAL passed review. A
dated epic with its own retrospective slot is the honest shape, and it
matches how Epics 35 and 38 were added.

**Effort / risk / timeline.** M + M; Low; no effect on the parked CAP-19 OQs
or Epic 39.4. It does gate cutover Phase 1: `python-foundry` must not inherit
either defect (review § 3 item 12).

## 4. Detailed change proposals

### Stories (new)

```
Epic: 40 — Red-team CRITICALs: verified mint, durable broker
Story: 40.1 IdP bearer is verified before mint   (spec-40-1-idp-bearer-is-verified-before-mint.md)
Story: 40.2 redis-broker is durable and bounded   (spec-40-2-redis-broker-is-durable-and-bounded.md)
```

Full intent contracts, ACs, Block-If and Never lists are in the two spec
files. Headline ACs:

- 40.1: the existing fake-`.sig` bearer returns **401**; wrong key / `none` /
  HS256 / wrong `iss` / wrong `aud` / expired / unknown-`kid`-twice all
  refused; station not in verified roles → **403**; verifier unconfigured →
  **503** in every profile; production stage-1 requires the three
  `COMPONENT_OIDC_*` keys; AST policy test forbids any other bearer decode.
- 40.2: broker PVC + `appendonly yes` + required `maxmemory` < required
  memory limit; cache unchanged; Celery results no longer stored; `applied:`
  keys carry TTL; stream trim declared, DLQ never auto-trimmed; a real
  `redis-server` kill/restart test proves stream, PEL, DLQ and `applied:`
  survive.

### SPEC (`spec-pyforge-unifying-strategy/SPEC.md`)

```
CAP-6 — One client, carrying identity.
OLD:  success: A service can independently verify which end user a portal call was made on behalf of …
NEW:  (unchanged) + Correct-course 2026-09-02: the host mint MUST verify the presented IdP
      bearer (signature via the configured JWKS, iss, aud, exp) before signing — Story 40.1.
      Never: a decode-only bearer path, in any profile.

CAP-11 — Queue and cache cannot evict each other.
OLD:  success: Filling the cache to its eviction limit provably loses no queued task.
NEW:  (unchanged) + Correct-course 2026-09-02: the broker is durable (AOF on a PVC) and bounded
      (maxmemory below its memory limit, noeviction) — a broker restart loses no queued task,
      stream entry, pending entry, DLQ entry or applied-id key — Story 40.2.
      Never: noeviction without maxmemory; emptyDir for the broker.
```

Rationale: both CAPs' *intent* already says this; the success clauses were
narrow enough to pass with the defect present. Constraints are appended, not
rewritten.

### Resilience invariants (`resilience-invariants.md`)

```
RFC-2 row — append: "2026-09-02: broker durable + bounded (Story 40.2); cache stays ephemeral."
RFC-3 row — append: "2026-09-02: mint verifies the IdP bearer against OIDC_JWKS_URL/OIDC_ISSUER/OIDC_AUDIENCE (Story 40.1); Token Exchange still deferred."
```

### Sibling SPEC (`spec-local-ocp-hybrid-environment/SPEC.md` CAP-3)

```
OLD:  CAP-3 — Redis hardened, ephemeral kept (→ Story 12.6). emptyDir stays (Celery re-queues) …
NEW:  (unchanged) + Superseded for the BROKER role 2026-09-02 by steward Story 40.2: the
      "Celery re-queues" premise does not cover Streams / PEL / DLQ / applied keys. Cache
      role stays as 12.6 shipped it.
```

### Dream (`docs/dreams/pyforge-unifying-strategy.md`)

- Grounding: one bullet under "Still open after the drain" naming Epic 40 as
  the red-team CRITICAL slice, and pointing at the review file.
- Realization log: dated 2026-09-02 entry (review landed; option 1 chosen;
  Epic 40 minted; HIGH set routed to a later correct-course).

### PRD (`prd-pyforge-unifying-strategy-2026-08-24/prd.md` § 14)

- Dated paragraph: Epic 40 precedes any further dispatch and cutover Phase 1.

### Epics (`epics.md`)

- Append Epic 40 with Stories 40.1 / 40.2 before the currency notes.

### Ledger (`sprint-status-ledger.yaml`)

- `40-1-idp-bearer-is-verified-before-mint: backlog`
- `40-2-redis-broker-is-durable-and-bounded: backlog`
- `epic-40: backlog`, `epic-40-retrospective: optional`; `# stories: 210`.

## 5. Implementation handoff

**Scope: Minor.** Route to the Developer agent (`bmad-build`) per story.

| Role | Responsibility |
|---|---|
| Operator (Rxm7706) | Yes/no on the two drafts; pick dispatch order (recommended 40.1 first). |
| Developer agent (`bmad-build` + spec) | Implement each story; `BMAD_ACTIVE_PROJECT=pyforge-steward`; physical paths; ledger `review` → `done` via `sprint-ledger-sync`. |
| Steward (owner) | Chart/values/bring-up docs review; CRC re-probe optional, not a stamp gate. |
| Warden | PR gate as usual; no second verdict. |

**Success criteria.** Both story ACs green; the two flipped invariant tests
and the new per-invariant durability test exist and fail-without/pass-with;
`epic-40` → `done`; review report R-1 and R-2 marked disposed. Then the
review's HIGH set (R-4 … R-16) goes through a second correct-course.

## 6. Applied

- `specs/spec-40-1-idp-bearer-is-verified-before-mint.md` (ready-for-dev)
- `specs/spec-40-2-redis-broker-is-durable-and-bounded.md` (ready-for-dev)
- `epics.md` Epic 40 / 40.1 / 40.2
- `sprint-status-ledger.yaml` four keys
- `spec-pyforge-unifying-strategy/SPEC.md` CAP-6, CAP-11 correct-course notes
- `spec-pyforge-unifying-strategy/resilience-invariants.md` RFC-2, RFC-3 notes
- `spec-local-ocp-hybrid-environment/SPEC.md` CAP-3 supersession note
- `docs/dreams/pyforge-unifying-strategy.md` Grounding bullet + Realization entry
- PRD § 14 dated paragraph
- `implementation-readiness-report-2026-09-02-red-team-critical.md`
- Review report: disposition line for R-1 / R-2
