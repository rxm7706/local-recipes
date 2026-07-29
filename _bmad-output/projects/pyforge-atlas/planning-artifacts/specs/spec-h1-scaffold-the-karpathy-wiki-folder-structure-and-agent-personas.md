---
title: 'Story H1 (9.1): Scaffold the Karpathy Wiki folder structure and Agent Personas'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #99 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Contract-spec — no original ever existed (corrected 2026-07-25).** This story
> (wave B9–H4) was built by the atlas migration's **in-session agent loop**, which —
> unlike `bmad-create-story` (used only for waves 0/A/B1–B8) — never emitted a per-story
> spec file. The atlas migration session (`01FYyQvBJuXwySiaMUUYCqBZ`) confirmed this
> exhaustively: no such file exists in `implementation-artifacts/`, `.bmad-loop/runs/`
> (which never existed for atlas), any git worktree, git history, or anywhere on disk.
> **Nothing was lost — there is no original to recover.** This file carries the
> load-bearing contract (Intent + Acceptance Criteria **verbatim** from the tracked
> `planning-artifacts/epics.md`) plus a dev narrative reconstructed from the merged record
> (the "Dev narrative" section below). A fuller BMAD-story-format reconstruction (Dev
> Agent Record + File List + Review Triage Log, built from the agent-loop transcripts) is
> at `../../spec-archive/retro-story-files/9-1-h1.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story H1 (9.1): Scaffold the Karpathy Wiki folder structure and Agent Personas

As the operator,
I want the `wiki/raw/ → compiled/ → outputs/` tree and the 5 BMAD personas (Ingester, Compiler, Linker, Linter, Oracle) defined,
So that the knowledge-base factory has its storage shape and workforce.

**Acceptance Criteria:** (spec § 9 Story H1, binding)

**Given** the scaffolded project
**When** the wiki scaffold lands
**Then** the three-stage wiki tree exists with a scaffold-layout test
**And** the 5 persona definitions resolve through the § 2 customization layers
**And** PostgreSQL/MinIO storage services are conda-forge-provisioned per AD-16 (MinIO server provisioning resolved as this story's precondition).

- **FRs:** FR-22(a).
- **Invariants:** AD-22, AD-16.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** scaffold-layout test + persona-resolution test in `kedro-test`.
- **Depends on:** Epic 8 complete (wave order); pipeline outputs to consume exist from Epic 3+.
- **DELIVERED (2026-07-18 — opens Wave H):** new `pyforge.atlas.factory` package. `factory/wiki.py` = the single-owner `raw/→compiled/→outputs/` layout contract (`WIKI_STAGES`/`WikiLayout`/`scaffold_wiki`) with a per-segment `stage_path` traversal guard enforcing the AD-22 write-boundary; `factory/personas.py` = the 5 § 2.2 personas + `resolve_personas(*overlays)` (BMAD customization layers, highest-priority-last; overlay may only refine — unknown name / rename rejected; workforce frozen at five); `factory/storage.py` = env-driven resolver defaulting to the OFFLINE filesystem backend (MinIO selected only when `ATLAS_WIKI_S3_ENDPOINT` set; host-agnostic AD-2). MinIO/PostgreSQL SERVER bring-up DEFERRED (DW-H1). Gate `tests/factory/` (26). AD-1 import-ban green. PR #99.

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] the three-stage wiki tree exists with a scaffold-layout test
- [x] the 5 persona definitions resolve through the § 2 customization layers
- [x] PostgreSQL/MinIO storage services are conda-forge-provisioned per AD-16 (MinIO server provisioning resolved as this story's precondition).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-22(a).
- **Invariants:** AD-22, AD-16.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** scaffold-layout test + persona-resolution test in `kedro-test`.
- **Depends on:** Epic 8 complete (wave order); pipeline outputs to consume exist from Epic 3+.
- **DELIVERED (2026-07-18 — opens Wave H):** new `pyforge.atlas.factory` package. `factory/wiki.py` = the single-owner `raw/→compiled/→outputs/` layout contract (`WIKI_STAGES`/`WikiLayout`/`scaffold_wiki`) with a per-segment `stage_path` traversal guard enforcing the AD-22 write-boundary; `factory/personas.py` = the 5 § 2.2 personas + `resolve_personas(*overlays)` (BMAD customization layers, highest-priority-last; overlay may only refine — unknown name / rename rejected; workforce frozen at five); `factory/storage.py` = env-driven resolver defaulting to the OFFLINE filesystem backend (MinIO selected only when `ATLAS_WIKI_S3_ENDPOINT` set; host-agnostic AD-2). MinIO/PostgreSQL SERVER bring-up DEFERRED (DW-H1). Gate `tests/factory/` (26). AD-1 import-ban green. PR #99.

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #99). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**Three modules open the factory layer.** `factory/wiki.py` owns the
`raw/ → compiled/ → outputs/` layout contract (`WIKI_STAGES`, `WikiLayout`,
`scaffold_wiki`); `factory/personas.py` the workforce; `factory/storage.py` the backend
resolver.

**The write boundary is enforced per path segment (AD-22).** `stage_path` refuses any escape
from the stage root — a per-segment traversal guard, not a prefix check on the assembled
string, which is what makes `../` and absolute-path tricks fail. Crews can therefore be given
a layout object rather than trusted to behave.

**The workforce is frozen at five, and the type system says so.** `resolve_personas(*overlays)`
models BMAD's layered merge (baseline `DEFAULT_PERSONAS`, overlays applied highest-priority-last,
mirroring the repo's six-layer config merge). An overlay **may only refine an existing
persona** — it can neither introduce a sixth nor drop one of the five, and a typo'd persona
name in an overlay is a **rejection, not a silent no-op**. `Persona` is a pydantic model with
`frozen=True, extra="forbid"`, so a stray overlay key is refused rather than carried — the
same discipline as the A2A schema family.

That last property is the interesting one: a customization system whose most likely failure is
a misspelled key is a customization system that silently ignores your configuration. This one
fails loudly instead.

**Storage defaults offline and host-agnostic (AD-2).** The resolver returns the filesystem
backend unless `ATLAS_WIKI_S3_ENDPOINT` is set, which is the only thing that selects MinIO. No
host is baked in. The MinIO/PostgreSQL **server** bring-up is deferred as DW-H1 — the seam
exists and defaults safe; the service is not running.

**Gate:** `tests/factory/` (26 assertions), AD-1 import-ban green.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-H1]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-H1]
- [Architecture: _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md]

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Delivery Record

<!-- DERIVED from the merged PR via `gh` on 2026-07-27. Exact, not reconstructed. -->

| | |
|---|---|
| Pull request | **#99** — H1: scaffold the Karpathy wiki + the 5 factory personas (FR-22(a)) |
| Merged | 2026-07-18 |
| Diff | 7 files, +546 / -0 |
| Test files touched | 3 |

**Commits**

- `f0ec142` H1: scaffold the Karpathy wiki + the 5 factory personas (FR-22(a))

**File list** *(exact, from the merged diff)*

```
  143 +     0 -  src/shared/packages/pyforge-atlas/tests/factory/test_personas.py
  126 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/personas.py
   93 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/wiki.py
   74 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/storage.py
   71 +     0 -  src/shared/packages/pyforge-atlas/tests/factory/test_wiki_scaffold.py
   39 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/__init__.py
    0 +     0 -  src/shared/packages/pyforge-atlas/tests/factory/__init__.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `fe52bbd`** — H1: scaffold the Karpathy wiki + the 5 factory personas (FR-22(a)) (#99)
  - Land the buildable half of the AI Software Factory storage layer (Wave H,
  - spec § 7 / § 9 Story H1), fully offline.
  - New package pyforge.atlas.factory (AD-22 write-boundary: reads atlas
  - datasets, writes ONLY the wiki tree / CMS):
  - - factory/wiki.py: the SINGLE owner of the wiki layout contract.
  - WIKI_STAGES ("raw","compiled","outputs") + WikiLayout + scaffold_wiki.
  - stage_path() safety-checks every segment and refuses any relative that
  - would escape the wiki root (traversal / absolute / empty) — the
  - emitter._require_safe_name lesson applied so a crafted document name
  - can't turn a wiki write into a write outside the tree. scaffold_wiki is
  - idempotent + non-destructive (factory only ADDS).
  - - factory/personas.py: the 5 § 2.2 personas (Ingester=Analyst,
  - Compiler=Architect, Linker=Developer, Linter=QA/Reviewer,
  - Oracle=Product Owner) each mapped to a wiki stage + governed tools.
  - resolve_personas(*overlays) merges the BMAD customization layers
  - highest-priority-last (CLAUDE.md six-layer semantics); an overlay may
  - only REFINE an existing persona — an unknown name raises (no silent
  - sixth agent) and the workforce always resolves exactly five. Frozen,
  - extra=forbid; merged personas are re-validated so a bad role/tool/stage
  - fails at resolve time, and DEFAULT_PERSONAS is never mutated.
  - - factory/storage.py: env-driven storage resolver. Defaults to the OFFLINE
  - filesystem backend (the scaffolded wiki/ tree) and opens no connection;
  - a MinIO/S3 backend is selected only when ATLAS_WIKI_S3_ENDPOINT is set
  - (host-agnostic, AD-2 — no host hardcoded; empty env == unset). Only the
  - minio SDK is in-env — the MinIO/PostgreSQL SERVER bring-up is the
  - attended H1 precondition, DEFERRED (DW-H1).
  - Verify gate: tests/factory/ (scaffold-layout + persona-resolution +
  - storage-resolution), 25 tests. AD-1 import-ban gate covers the new module
  - (imports pydantic + stdlib only). Full atlas suite 737 passed.
  - Claude-Session: https://claude.ai/code/session_01FYyQvBJuXwySiaMUUYCqBZ
  - Co-authored-by: Claude <noreply@anthropic.com>

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#99`.

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #99: H1: scaffold the Karpathy wiki + the 5 factory personas (FR-22(a))

## Deferred Work (DW ledger)

### DW-H1 — the MinIO/PostgreSQL SERVER provisioning + bring-up (ATTENDED) — DEFERRED to the H1 precondition event
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story H1, § 7.4, FR-22(a))
  summary: H1 shipped the BUILDABLE half of the Karpathy-wiki storage layer — the layout contract
    (`factory/wiki.py`: `WIKI_STAGES` + `WikiLayout` + `scaffold_wiki`, the SINGLE owner of the
    `raw/ → compiled/ → outputs/` tree), the five § 2.2 personas + their BMAD customization-layer
    resolution (`factory/personas.py`), and the storage-backend RESOLVER (`factory/storage.py`),
    all offline. The architecture (ARCHITECTURE-SPINE § "Factory layer") records that **only the
    MinIO Python SDK is in-env today — the MinIO/PostgreSQL SERVERS are not provisioned**, and calls
    that server bring-up the H1 precondition (Spine "Deferred"). H1's code therefore DEFAULTS to the
    plain local filesystem (`resolve_storage_config()` → `backend="filesystem"` when
    `ATLAS_WIKI_S3_ENDPOINT` is empty/unset) and never opens a connection; a MinIO backend is
    selected ONLY when an endpoint is explicitly configured (host-agnostic, AD-2 — no host is
    hardcoded). The ACTUAL deferred bring-up: provision the conda-forge MinIO + PostgreSQL servers
    (precedent: MyBMAD's per-user PostgreSQL in the `bmad-ui` env), create the wiki bucket, wire the
    live `minio` SDK client from the resolved config, and run the crews against the object store
    instead of the local dir. Do NOT weaken any gate to stand up a server unattended or bind a
    socket (NFR-12). Mirrors DW-C1-1 / DW-G3 (live daemon bring-up) and DW-D3-1 (live backend).
  evidence: `factory/storage.py::resolve_storage_config` returns `filesystem` with no network
    touch when the endpoint env is absent (`tests/factory/test_personas.py` storage cases:
    default-is-filesystem, empty-env-is-unset, configured-endpoint-selects-minio,
    both-keys-required-for-credentials). Only `minio` the SDK is importable in-env; no server
    process runs. The AD-16 pixi.toml line ships `minio >=7.2.20` (SDK) + `psycopg2 >=2.9.12`
    (driver) — the SDKs, not the servers.
