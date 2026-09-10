---
title: Sprint Change Proposal — parent AD-1 / canopy:AD-13 reopened (object storage vs RWX media)
date: 2026-09-05
project: pyforge-steward
chain: pyforge-unifying-strategy (extends spec-python-agent-platform)
status: approved — Option A, applied 2026-09-05 in the same PR
trigger: docs/dreams/foundry-baas-capability-gaps.md § "Reopening AD-1" (seed Dream, PR #1053, 2026-09-05) — its recommendation 6 asks for a formal correct-course on `pap:AD-1` and canopy `canopy:AD-13` instead of a silent reversal
mode: batch
scope: minor — architecture prose amendments plus three doc lines; no new infra kind, no story, no ledger change (under Option A)
operator: Rxm7706
follows: sprint-change-proposal-2026-09-04-foundry-cutover.md
---

# Sprint Change Proposal — parent AD-1 / canopy:AD-13 reopened

## 1. Issue summary

The seed Dream `foundry-baas-capability-gaps.md` (merged 2026-09-05) claims that parent
`AD-1` ("Infrastructure is exactly PostgreSQL + Redis + Kubernetes") and canopy `canopy:AD-13`
(Lane 1 media on a `ReadWriteMany` PVC) "were asserted with a weaker justification than
their own documentation claims", on two legs:

1. **Air-gap leg** — the air-gap argument does not distinguish self-hosted object storage
   from self-hosted PostgreSQL/Redis; this repo already trusts that substitution via JFrog
   Artifactory.
2. **RWX leg** — the RWX-PVC alternative was asserted, not verified; at `replicaCount: 1`
   an ordinary `ReadWriteOnce` PVC already solves the live problem; the target cluster's
   storage class may not support RWX at all.

This pass re-read the primary sources (not the seed's summary of them). Both legs need
correction; what survives is a different, narrower finding.

**Leg 1 does not hold.** Parent `AD-1`'s complete text
(`specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md:25`):

> Infrastructure is exactly PostgreSQL + Redis + Kubernetes. A component that demands a
> fourth piece of infrastructure has failed its design review. pgvector rides inside the
> same PostgreSQL instance (AD-5) and Redis carries both cache and Celery-broker duty —
> neither is a licence for a fourth piece.

There is no air-gap clause. Air-gap parity is a *separate* decision (parent `canopy:AD-13` /
`pap:CAP-6`), and neither the canopy's inherited-AD table (canopy spine line 85), its
conflict paragraph (line 98), nor canopy `canopy:AD-13` itself (line 184) cites air-gap as the
reason for the media rule — all three justify it by kind-count alone. The rule's own
documentation presents exactly what it is: a design-review discipline the operator
ratified, a judgment call and never a physics claim. The Artifactory precedent is real
(`docs/reference/enterprise-deployment.md`) and irrelevant to a rule that never invoked
air-gap.

**Leg 2 half-holds, and the half that holds is a different finding.**

- *"Never verified"* — false. The Story 12.7 live-cluster record
  (`specs/spec-12-1-…-verification-2026-08-25.md` § Proofs, "PVC binding") shows the
  `platform-media` RWX claim **Bound** on CRC 2.63.0 / OpenShift 4.22.7, StorageClass
  `crc-csi-hostpath-provisioner`. Story 20.2's `done` rests on a live bind, not only on the
  Helm-render assertion at `src/platform/tests/test_chart_invariants.py:1999`.
- *"RWO suffices at `replicaCount: 1`"* — false. **Five** platform Deployments mount the
  `wagtail-media` volume — web (`platform-deployment.yaml`), `worker`, `worker-builds`,
  `beat`, `consume-events` — and the invariant test asserts web + worker. Two pods on two
  nodes need `ReadWriteMany` regardless of the web replica count. `replicaCount: 1`
  (`values.yaml:11`) is verified and not decisive.
- *What survives* — CRC is single-node, and a hostpath CSI provisioner satisfies RWX
  trivially (it also ignores `size`: finding 1 of the same record). No multi-node target
  exists yet, and `media.persistence.storageClassName: ""` (`values.yaml:256`) defers to the
  cluster's default class, which on most multi-node provisioners is RWO-only. On such a
  cluster the media PVC sits `Pending` and every Deployment that mounts it never schedules.
  Nothing names this prerequisite: not the chart comment (`values.yaml:250`), not
  `media-pvc.yaml`, not `NOTES.txt:22`, not `deploy/DR.md:15`, and `deploy/README.md:211`
  still reads "No HPA/PDB/media PVC — out of scope", stale since 20.2 shipped. This is a
  **missing-architecture** gap, not an `AD-1` gap.
- *Also surfaced* — "review-blocking until parent AD-1 is formally excepted" appears three
  times (canopy spine 98 and 184; `resilience-invariants.md:106` BS-8), and no artifact
  defines what a formal exception is. Parent `AD-6` already shows the shape: a dated,
  bounded, scoped exception paragraph appended under the AD (the DB-GPT SQLite PVC,
  2026-08-21), with the operator ruling recorded in the Dream first.

**Problem type:** misread requirements (seed leg 1, and the RWO half of leg 2) plus missing
architecture (the RWX storage-class prerequisite; the undefined exception procedure).

## 2. Change-navigation checklist (recorded)

| # | Item | Status | Finding |
|---|---|---|---|
| 1.1 | Triggering story | Done | None red. Trigger is the seed Dream's recommendation 6. Story 20.2 is `done` and its bind is proven on CRC. |
| 1.2 | Problem type | Done | Misread requirements + missing architecture. Not a technical limitation; not a strategic pivot. |
| 1.3 | Evidence | Done | Parent spine AD-1 / AD-6 / canopy:AD-13; canopy spine 85 / 98 / 100 / 184; 12.1 verification § Proofs + finding 1; `values.yaml` 11 / 250–256; `media-pvc.yaml`; the five mounting templates; `test_chart_invariants.py` 1999 / 2052; `deploy/README.md:211`; `DR.md:15`; `resilience-invariants.md:106`; `epics.md:1343` (NFR-C2), `:1583` (20.2). |
| 2.1 | Current epic completable | Done | Epic 20 stays `done`; nothing reopens. |
| 2.2 | Epic-level change | Done | None. |
| 2.3 | Remaining epics | Done | Epic 44 inherits `pap:AD-1..17` and canopy `AD-1..23` read-only; the `fnd` spine carries no media or storage decision. Unaffected. |
| 2.4 | New epics | Done | None. Object-storage as a product (seed Scopes B / C) is outside this chain by the seed's own verdict. |
| 2.5 | Order / priority | N/A | — |
| 3.1 | PRD | Done | FR-8 ("media and cache survive multiple replicas") and NFR-C2 stand as written. No FR change. |
| 3.2 | Architecture | Action-needed | canopy:AD-13 gains the storage-class prerequisite and the multi-mount reason; the canopy conflict paragraph defines the exception procedure; parent AD-1 gets a dated re-affirmation in the AD-6 style. |
| 3.3 | UI/UX | N/A | — |
| 3.4 | Other artifacts | Action-needed | Dream Grounding bullet + Realization entry; seed Dream § Reopening gets a dated correction so the later fold carries the corrected finding; `deploy/README.md:211`, `values.yaml:250`, `NOTES.txt:22`. |
| 4.1 | Direct adjustment | Viable | Prose plus three doc lines. Effort **Low**. Risk **Low**. |
| 4.2 | Rollback | Not viable | Nothing to revert; 20.2 is proven. |
| 4.3 | MVP review | Not viable | Scope unchanged. |
| 4.4 | Path | Done | Direct adjustment — **Option A** below. |
| 6.3 | Approval | Action-needed | Operator rules A / B / C. |
| 6.4 | Ledger | N/A under A | A mints no story. B or C would mint one (see § 3). |

## 3. Options and recommended approach

**Option A — Re-affirm AD-1 and canopy:AD-13; amend canopy:AD-13's prerequisite; define the exception
procedure. (Recommended.)** Scope minor. No new kind, no story, applied in one PR. The two
decisions stand on the justification they actually gave; the real gap (an RWX-capable storage
class is a deploy prerequisite nobody wrote down) closes as prose in the spine and three doc
lines in the chart. "Formally excepted" becomes a defined path so a future need does not
restart this analysis.

**Option B — Except parent AD-1 for a self-hosted, in-cluster S3-compatible store for Lane 1
media.** What it costs, so the price is on record: a `django-storages` S3 backend with
credentials through parent canopy:AD-12; a MinIO / ODF-RGW workload (Helm, an image mirror for
air-gap parity, SCC posture, a DR.md row, a backup path); BS-8's Mason boot re-index revisited
against an object store; `test_chart_templates_forbid_minio_s3_and_elasticsearch` inverted;
canopy:AD-13 rewritten; a dated Dream entry *first* (the parent canopy:AD-14 pattern). No evidence in
this pass says it is needed — RWX binds on the only target that exists, and the seed itself
disclaims MinIO as the answer. Not recommended now. If chosen: one steward story, `blocked`
until the Dream entry lands.

**Option C — Amend canopy:AD-13 to `ReadWriteOnce` while `replicaCount: 1`.** Rejected on
evidence: five Deployments mount the volume, and RWO works only if all five are co-scheduled
on one node, which nothing in the chart enforces. Choosing C would make the next multi-node
install fail in a new way.

## 4. Detailed change proposals (Option A)

### 4.1 Canopy spine — `canopy:AD-13` Rule (line 184)

**OLD (tail):** `… is a fourth infra kind (parent AD-1) and a review-blocking finding until
that parent AD is formally excepted.`

**NEW (tail):** `… is a fourth infra kind (parent AD-1) and a review-blocking finding until
that parent AD is formally excepted (procedure: § *Conflict, not override — parent AD-1*).
**Prerequisite (2026-09-05):** the media PVC is mounted by every platform Deployment (web,
worker, worker-builds, beat, consume-events), so `ReadWriteMany` is required at any replica
count on a multi-node cluster — not only for web replicas. RWX is proven on CRC
(`crc-csi-hostpath-provisioner`, single-node; 12.1 verification 2026-08-25). A multi-node
target must name an RWX-capable class in `media.persistence.storageClassName` before install;
a media PVC left `Pending` is the failing check, not a warning.`

Rationale: records the only thing the reopening actually found — an unstated prerequisite —
and the structural reason RWO is not an alternative.

### 4.2 Canopy spine — "Conflict, not override — parent AD-1" (line 98)

**Append:** `**Formal exception (defined 2026-09-05):** a dated, bounded paragraph appended
under the parent AD in `spec-python-agent-platform/ARCHITECTURE-SPINE.md` in the AD-6 style —
what is excepted, why the three kinds cannot carry it, its scope, its cost — preceded by a
dated entry in the owner Dream and a correct-course proposal recording the operator ruling.
Re-examined 2026-09-05 (`sprint-change-proposal-2026-09-05-ad-1-reopen.md`): **re-affirmed,
not excepted.**`

Rationale: three artifacts gate on a procedure none of them defines.

### 4.3 Parent spine — `AD-1` (line 25, append a paragraph in the AD-6 exception style)

**Append:** `**Re-affirmed, 2026-09-05.** Re-examined against
`docs/dreams/foundry-baas-capability-gaps.md` § *Reopening AD-1*. This rule is design-review
discipline — a bound on operational surface — and has never rested on air-gap parity (that is
canopy:AD-13). Lane 1 media stays on a `ReadWriteMany` PVC (canopy:AD-13, prerequisite added the same
day). No exception granted. Exception procedure: canopy spine § *Conflict, not override —
parent AD-1*.`

Rationale: the parent spine is inherited read-only by two chains; a dated note there is how
AD-6's exception was recorded, and it is where the next reader of AD-1 will look.

### 4.4 Dream `docs/dreams/pyforge-unifying-strategy.md`

- Grounding bullet (lines 338–339). **OLD:** `No MinIO as a fourth core kind.` **NEW:** `No
  MinIO as a fourth core kind (re-affirmed 2026-09-05; Lane 1 media is RWX, and a multi-node
  target names its RWX storage class).`
- Realization log, new entry **2026-09-05** — the correct-course ran; both seed legs
  corrected against primary sources; AD-1 / canopy:AD-13 re-affirmed; prerequisite and exception
  procedure recorded; seed fold still pending.

### 4.5 Seed Dream `docs/dreams/foundry-baas-capability-gaps.md`

- § *Reopening AD-1*: prepend a dated **Correction (2026-09-05, correct-course)** block
  stating the two corrections and the surviving finding, so the later fold (deferred step a)
  carries the corrected text rather than the original claims.
- Realization log entry for the same date. Frontmatter unchanged (`status: draft`).

### 4.6 Doc lines under `src/platform/` (same PR; droppable without affecting 4.1–4.5)

- `deploy/README.md:211` — **OLD:** `- No HPA/PDB/media PVC — out of scope for the current
  chart stories.` **NEW:** `- No HPA/PDB. Media is an RWX PVC (Story 20.2, canopy:AD-13)
  mounted by every platform Deployment; on a multi-node cluster set
  `media.persistence.storageClassName` to an RWX-capable class or the claim stays Pending.
  Proven on CRC (`crc-csi-hostpath-provisioner`).`
- `charts/platform/values.yaml:250` comment — add: `Needs an RWX-capable StorageClass on a
  multi-node cluster; "" = the cluster default, which is often RWO-only.`
- `charts/platform/templates/NOTES.txt:22` — `(ReadWriteMany — needs an RWX-capable
  StorageClass on multi-node clusters)`.

No template logic changes; `test_chart_invariants.py` unaffected.

## 5. Implementation handoff

**Scope: Minor.** Developer (this session) applies 4.1–4.6 on approval, in one branch off
`main`, PR to `rxm7706/local-recipes` with the `maintenance` label (paths outside `recipes/`).
Gates before the PR: `dreams-hygiene-check`, `dream-chain-check`, `chain-completeness-check`,
`spec-surface-check` (re-stamp scoped if the canopy spine or Dream sits in a baseline),
`detectors-ci` diffed against `main`. No ledger write. Success: gates no worse than `main`;
the four prose sites agree on the same three facts (no air-gap clause, RWX proven on CRC,
storage class is a prerequisite).

**Explicitly not in this proposal:** the seed Dream's five capability candidates and its fold
into the Unifying Strategy (deferred step a, next); any object-storage work (Option B, not
chosen).

## 6. Operator ruling

**2026-09-05 — Option A.** Parent AD-1 and canopy:AD-13 re-affirmed; the RWX storage-class
prerequisite and the exception procedure are recorded; the three `src/platform` doc lines ship in
the same PR. The five follow-up-review branches (41.3, 41.4, 42.1, 42.2, 43.2) land after this PR.

## 7. Applied (2026-09-05)

- Canopy spine: canopy:AD-13 Rule prerequisite (4.1); "Conflict, not override — parent AD-1" exception
  procedure + re-affirmation (4.2); `updated: 2026-09-05`.
- Parent spine: dated re-affirmation paragraph under AD-1 (4.3).
- Dream `pyforge-unifying-strategy.md`: Grounding infra-kinds bullet; Realization entry (4.4).
- Seed Dream `foundry-baas-capability-gaps.md`: dated correction block at the top of § *Reopening
  AD-1*; Realization entry; frontmatter unchanged (4.5).
- `src/platform/deploy/README.md:211`, `charts/platform/values.yaml` media comment,
  `templates/NOTES.txt` media line (4.6). No template logic; no test change.
- Spec-surface baseline re-stamped scoped to the specs whose sources changed (see PR).
