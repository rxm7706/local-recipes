---
title: Sprint Change Proposal — AD-1 object-storage exception (StorageGRID, consumed not self-hosted)
date: 2026-09-10
project: pyforge-steward
chain: pyforge-unifying-strategy
status: approved — Option B, applied 2026-09-10 in the same PR
trigger: docs/dreams/platform-object-storage-kind.md (seed Dream, 2026-09-10) — the exact scenario the 2026-09-05 proposal named and deferred ("Explicitly not in this proposal: ... any object-storage work (Option B, not chosen)")
mode: batch
scope: moderate — one dated exception paragraph, one new Epic (three stories), no ledger regression
operator: Rxm7706
follows: sprint-change-proposal-2026-09-05-ad-1-reopen.md
---

# Sprint Change Proposal — AD-1 object-storage exception

## 1. Issue summary

`spec-pyforge-unifying-strategy/SPEC.md`'s own Constraints (the AD-1 text, merged in
from `spec-python-agent-platform` by Story 48.8): *"infrastructure is exactly
PostgreSQL + Redis + Kubernetes. A component demanding a fourth backing service has
failed its design review."* `stack.md`'s own "Never" list names the two things this
rule was written to stop: *"a fourth backing service (Vault-in-pod, MinIO, extra
bus)."*

The 2026-09-05 proposal (`sprint-change-proposal-2026-09-05-ad-1-reopen.md`)
re-examined this rule once already, for Lane 1 media specifically, and re-affirmed
it — a Kubernetes RWX PVC covers that case, no exception needed — while explicitly
scoping object storage itself out: *"Explicitly not in this proposal: ... any
object-storage work (Option B, not chosen)."*

That deferred scenario is now live. The air-gap deployment target will have
**NetApp StorageGRID** (S3-compatible object storage) as infrastructure the
operations team already runs — the same way it already runs the Kubernetes cluster
and the identity provider. Nothing in the estate can point at it today.

**The distinction this pass draws, that the 2026-09-05 pass didn't need to:**
both examples `stack.md` names — Vault-in-pod, self-hosted MinIO — are things
pyforge would deploy and operate inside its own Helm chart. AD-1's own rule exists
to stop the estate from becoming the *operator* of a fourth infrastructure kind.
StorageGRID is not that: it's ops-provided and externally operated, the same
consumption shape the estate already trusts for the identity provider
(`canopy:AD-19`: *"pod specs carry secret references only; no Vault HTTP from the
platform image. Cluster ESO/Vault stays outside the image"*). Consuming an
externally-operated S3 endpoint via a client library was never what the rule
forbade; self-hosting one was and remains forbidden.

## 2. Impact analysis

**Spec impact.** `spec-pyforge-unifying-strategy/SPEC.md`'s AD-1 Constraint gains one
dated, bounded exception paragraph (§4.1 below) — the rule's own text is not
rewritten, only extended, matching the 2026-09-05 precedent's own technique
(a dated re-affirmation paragraph appended under the rule, never an edit to the
rule's own sentence).

**Dream impact.** `docs/dreams/platform-object-storage-kind.md` gains a Realization-
log entry recording this proposal's outcome (§4.2), same as the owner Dream did for
the 2026-09-05 pass.

**Epic/story impact.** No existing story or epic changes shape. A new Epic 50 is
minted on `pyforge-steward` (§4.3) carrying three stories: the Silo conda-forge
recipe, the local-dev pixi tooling (Silo default, Garage alternative), and a minimal
S3-client seam. None touch Lane 1 media or any other already-shipped feature.

**No ledger regression.** All three new story keys mint `backlog` — nothing flips a
`done` row backward.

**Technical impact.** None yet — this proposal authorizes the exception and mints
the stories; the stories themselves do the file-level work (new recipe, new pixi
feature, new `src/platform/` module).

## 3. Recommended approach

**Direct adjustment — mint a new epic, no rollback or MVP-scope change.** This is
new capability, additive to the estate, with a narrow and precisely-bounded
exception (object storage only, client-consumed only, never self-hosted). Effort:
moderate (three stories, one of which is real conda-forge recipe work with its own
lifecycle). Risk: low — the exception's own boundary (never a platform-image-
deployed service) is the same boundary AD-19 already proved safe for the IdP.
Timeline: no dependency on anything currently in flight.

## 4. Detailed change proposals

### 4.1 — `spec-pyforge-unifying-strategy/SPEC.md`, AD-1 Constraint

**OLD** (the existing bullet, unchanged, immediately followed by the new one):

> - **Always:** infrastructure is exactly PostgreSQL + Redis + Kubernetes. A component
>   demanding a fourth backing service has failed its design review. DuckDB is a
>   **library / query face** (in-process or an optional `duckdb-server` process on
>   the platform image), not a fourth Helm backing store.

**NEW** (appended immediately after, as its own bullet):

> - **Exception (dated 2026-09-10, AD-1 object storage).** An S3-compatible object
>   store is permitted as a *consumed*, never *self-hosted*, backing service — the
>   same shape `canopy:AD-19` already trusts for the identity provider (pod specs /
>   application config carry an endpoint URL and credentials only; no object-storage
>   server process ships inside the platform image or Helm chart). Production target:
>   NetApp StorageGRID, ops-provided and externally operated. This does not reopen
>   Lane 1 media's own 2026-09-05 re-affirmation (RWX PVC stands); it authorizes
>   object-storage *consumption* for capability that specifically needs S3 API
>   semantics, decided story-by-story, never assumed. Self-hosting MinIO, Silo,
>   Garage, or any object-store server inside the deployed platform remains
>   forbidden without a further, separately-justified exception.

### 4.2 — `docs/dreams/platform-object-storage-kind.md`, Realization log

Append: *"2026-09-10 — processed via `bmad-correct-course`
(`sprint-change-proposal-2026-09-10-ad-1-object-storage-exception.md`). AD-1 gained
the dated consumed-not-self-hosted exception; decomposed into steward Epic 50
(Stories 50.1-50.3): the Silo conda-forge recipe, local-dev pixi tooling
(Silo default / Garage alternative), and a minimal S3-client seam. Status: pitched
→ specified."*

Frontmatter `status` moves `pitched` → `specified` (a Spec-equivalent artifact — this
proposal plus the epics decomposition — now exists for it, satisfying `dream-chain-
check`'s INV-1).

### 4.3 — New Epic 50 on `pyforge-steward`

```
## Epic 50: Object storage is consumable, without pyforge operating it

### Story 50.1: The Silo conda-forge recipe exists and is pixi-installable
### Story 50.2: Local-dev object storage — Silo default, Garage alternative, pixi-provisioned
### Story 50.3: A minimal S3-client seam proves the exception end-to-end
```

Full story bodies land in `epics.md` directly (Section 5); summarized here for the
proposal record:

- **50.1** (conda-forge-expert-invoking, per Rule 1): author `recipes/silo/recipe.yaml`
  wrapping `pgsty/silo`'s upstream release binaries; validate/optimize/scan/build
  locally; publish to the `SelfExplainML` anaconda.org channel so it is pixi-
  installable without waiting on upstream `conda-forge/staged-recipes` review.
- **50.2**: a new, separate pixi feature (not folded into `platform-dev`, matching
  the `scribe-pg`/pgvector win-64 precedent — Garage has no win-64 build) carrying
  `silo` + `garage`; a script mirroring `scripts/scribe_pg.py`'s `up`/`down`/`status`
  shape, backend selection via an env var mirroring
  `PYFORGE_SCRIBE_TRIGGER_BACKEND`'s pattern, default `silo`.
- **50.3**: a `src/platform/` module taking an S3 endpoint + credentials as
  configuration only (never hardcoded) — the same client code points at the local
  Silo/Garage instance or real StorageGRID interchangeably. One round-trip put/get
  test against the local backend. No consumer wired to it in this pass.

## 5. Implementation handoff

**Scope: Moderate.** Developer agent(s) implement 50.1-50.3 as three separate
dispatches (matching this session's own established `marshal factory dispatch`
workflow), each on its own branch, PR to `rxm7706/local-recipes` with the
`maintenance` label (paths outside `recipes/` for 50.2/50.3; 50.1 touches only
`recipes/silo/`, so no label needed there per this repo's own recipe-only-PR rule).

Gates before each PR: `dreams-hygiene-check`, `dream-chain-check`,
`chain-completeness-check`, `spec-surface-check` (scoped re-stamp), `detectors-ci`
diffed against `main`. 50.1 additionally: the CFE submission-ready gate
(`validate_recipe` + `optimize_recipe` + `scan_for_vulnerabilities` + a green
linux-64 build).

**Explicitly not in this proposal:** migrating Lane 1 media or any other existing
feature onto object storage; submitting the Silo recipe to upstream
`conda-forge/staged-recipes` (the normal, separate follow-up once the
`SelfExplainML`-staged version proves out); any production StorageGRID
credential/endpoint provisioning (that is an operator/ops action, out of this
repo's scope, the same boundary the IdP's own credentials already sit behind).

## 6. Operator ruling

**2026-09-10 — Option B.** AD-1 gains the dated, bounded object-storage exception;
Epic 50 (Stories 50.1-50.3) is minted `backlog` on `pyforge-steward`; Silo is the
default local-dev backend, Garage the pluggable alternative.

## 7. Applied (2026-09-10)

- `spec-pyforge-unifying-strategy/SPEC.md`: dated exception bullet under AD-1 (§4.1).
- Dream `docs/dreams/platform-object-storage-kind.md`: Realization-log entry,
  `status: pitched` → `specified` (§4.2).
- `epics.md`: Epic 50 minted, Stories 50.1-50.3 (§4.3).
- `sprint-status-ledger.yaml`: `50-1-...`, `50-2-...`, `50-3-...` minted `backlog`.
- Spec-surface baseline re-stamped scoped to the specs whose sources changed.
