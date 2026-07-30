---
title: 'Story H3 (9.3): Integrate La Suite Docs REST API Sync'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #101 body + main commit log; dev narrative recovered, review-triage partial)'
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
> at `../../spec-archive/retro-story-files/9-3-h3.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story H3 (9.3): Integrate La Suite Docs REST API Sync

As the operator,
I want `LaSuiteClient` + `WikiSyncer` pushing compiled wiki files to the Layer-1 CMS via the Wagtail/Django REST API,
So that humans read the factory's knowledge in the presentation layer.

**Acceptance Criteria:** (spec § 9 Story H3, binding)

**Given** the H2 compiled wiki output and a mock Wagtail API
**When** the sync runs
**Then** a round-trip fixture test passes against the mock (push, update, idempotent re-push).

- **FRs:** FR-22(c).
- **Invariants:** AD-22 (writes only wiki/CMS; idempotent re-push).
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** mock-Wagtail round-trip fixture in `kedro-test`.
- **Depends on:** H1, H2.
- **DELIVERED (2026-07-18):** `factory/lasuite.py` — `LaSuiteClient` (create/update/get/list over the Wagtail/Django REST shape; clear `LaSuiteError` on non-2xx AND on a 2xx-without-id, per § 2.1) + `WikiSyncer` (idempotent **outputs/**→CMS push keyed by content sha: new→create, changed→update, unchanged→SKIP with NO remote call). CMS source is `outputs/` (the Oracle's final reports, per the H1 layout contract + § 7.4), not internal `compiled/` (`source_stage` override available). Transport is the injected `opener` seam — package code holds no HTTP client (AC-2, no-inline-IO gate green); the default opener refuses clearly. Mapping sidecar lives at the wiki ROOT (AD-22), written ATOMICALLY (tmp+os.replace) and corruption-loud on load. Verified against an in-memory mock Wagtail (push/update/idempotent-re-push/mapping-resume). Live Wagtail server + httpx opener bring-up DEFERRED (DW-H3). Independent review found 3 SHOULD-FIX (malformed-2xx KeyError; non-atomic sidecar write; compiled-vs-outputs contract contradiction) + NITs — all fixed + regression-tested. Gate `tests/factory/test_lasuite.py`.

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] a round-trip fixture test passes against the mock (push, update, idempotent re-push).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-22(c).
- **Invariants:** AD-22 (writes only wiki/CMS; idempotent re-push).
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** mock-Wagtail round-trip fixture in `kedro-test`.
- **Depends on:** H1, H2.
- **DELIVERED (2026-07-18):** `factory/lasuite.py` — `LaSuiteClient` (create/update/get/list over the Wagtail/Django REST shape; clear `LaSuiteError` on non-2xx AND on a 2xx-without-id, per § 2.1) + `WikiSyncer` (idempotent **outputs/**→CMS push keyed by content sha: new→create, changed→update, unchanged→SKIP with NO remote call). CMS source is `outputs/` (the Oracle's final reports, per the H1 layout contract + § 7.4), not internal `compiled/` (`source_stage` override available). Transport is the injected `opener` seam — package code holds no HTTP client (AC-2, no-inline-IO gate green); the default opener refuses clearly. Mapping sidecar lives at the wiki ROOT (AD-22), written ATOMICALLY (tmp+os.replace) and corruption-loud on load. Verified against an in-memory mock Wagtail (push/update/idempotent-re-push/mapping-resume). Live Wagtail server + httpx opener bring-up DEFERRED (DW-H3). Independent review found 3 SHOULD-FIX (malformed-2xx KeyError; non-atomic sidecar write; compiled-vs-outputs contract contradiction) + NITs — all fixed + regression-tested. Gate `tests/factory/test_lasuite.py`.

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #101). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**Idempotency is keyed on content, and "unchanged" means no remote call at all.** `WikiSyncer`
keeps a content-sha mapping: new → create, changed → update, **unchanged → skip with no
request issued**. Re-running the sync against an unchanged wiki is therefore free and
side-effect-free, which is what makes it safe to put on a schedule.

**The CMS source is `outputs/`, not `compiled/`.** The Oracle's final reports are what gets
published; `compiled/` is internal. A `source_stage` override exists, but the default encodes
the H1 layout contract — publishing the intermediate stage would leak working state to a
public CMS.

**The package holds no HTTP client.** Transport is an injected `opener` seam, and the
**default opener refuses to run**, clearly. Raising rather than importing `httpx` is what
keeps the module IO-free and offline by default — and keeps the no-inline-IO gate green (AC-2).

**Errors are written for an agent to act on.** `LaSuiteError` names the method, URL, status,
and body, so a retry or repair can reason about the failure without parsing a traceback
(§ 2.1 — agents auto-diagnose). It is raised on non-2xx **and on a 2xx that carries no id**,
which is the failure mode a naive client turns into a `KeyError` three frames away.

**Config resolves from env or not at all (AD-2).** `resolve_lasuite_config` requires **both** a
base URL and a token, returning `None` otherwise — a half-configured target never becomes a
push at a public or partial endpoint. Same posture as D3's backend resolver.

**The mapping sidecar is written atomically.** tmp + `os.replace`, at the wiki root, and
corruption-loud on load. An interrupted sync must not leave a mapping that silently
mis-associates local docs with remote ids.

**Verified against an in-memory mock Wagtail** — push, update, idempotent re-push, and mapping
resume — with no network. Live server and the httpx opener are DW-H3.

**Independent review found three SHOULD-FIX** — the malformed-2xx `KeyError`, the non-atomic
sidecar write, and a contradiction between the compiled-vs-outputs contract and the code — all
fixed and regression-tested before merge. The third was a spec/code disagreement, and the code
was brought to the contract rather than the contract quietly reinterpreted.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-H3]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-H3]
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
| Pull request | **#101** — H3: La Suite / Wagtail REST wiki sync (FR-22(c)) |
| Merged | 2026-07-18 |
| Diff | 4 files, +569 / -0 |
| Test files touched | 1 |

**Commits**

- `3d8e21f` H3: La Suite / Wagtail REST wiki sync (FR-22(c))

**File list** *(exact, from the merged diff)*

```
  291 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/lasuite.py
  263 +     0 -  src/shared/packages/pyforge-atlas/tests/factory/test_lasuite.py
   14 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/factory/__init__.py
    1 +     0 -  _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `4e95efb`** — H3: La Suite / Wagtail REST wiki sync (FR-22(c)) (#101)
  - Implement the wiki -> CMS sync (Wave H, spec § 7.1 / § 9 Story H3) that
  - pushes the Karpathy wiki's final reports up to the Layer-1 Wagtail/La Suite
  - CMS.
  - factory/lasuite.py (stdlib + .crews/.wiki only — no HTTP client in package
  - code, AC-2 no-inline-IO gate green):
  - - LaSuiteClient: create/update/get/list documents over the Wagtail/Django
  - REST shape. Owns base_url + bearer auth (from LaSuiteConfig); delegates
  - the wire to an INJECTED `opener` (the sole network seam — like the
  - B5/B7/B8 dataset refresher/fetcher injection). Non-2xx -> a clear
  - LaSuiteError naming method/url/status/body (§ 2.1). The default opener
  - REFUSES (no transport injected) rather than importing httpx — the live
  - opener is the attended bring-up (DW-H3).
  - - WikiSyncer: idempotent outputs/ -> CMS push keyed by content digest. Reads
  - wiki/outputs/ by default (the Oracle's FINAL reports for the human CMS,
  - per the H1 layout contract + § 7.4 — NOT the internal compiled/
  - knowledge-graph stage; source_stage overrides). A local mapping
  - (<wiki-root>/.lasuite_sync.json: {relpath: {id, sha}}) records the CMS doc
  - id + last-synced sha per file, so: new -> CREATE, changed -> UPDATE (never
  - a duplicate create), unchanged -> SKIP with ZERO remote calls (§ 2.1
  - idempotent-first). The mapping lives at the wiki ROOT (AD-22), is written
  - ATOMICALLY (tmp + os.replace, mirroring datasets/refresh.py) so a mid-save
  - crash can't corrupt the idempotency key, and a corrupt mapping fails
  - LOUDLY on load (never silently empty -> which would duplicate-create every
  - page). A 2xx create body lacking `id` is a clear error, not a bare
  - KeyError. Title prefers frontmatter, then a heading, then the stem, and is
  - never empty.
  - Endpoint + token resolve only from env (LASUITE_BASE_URL / LASUITE_API_TOKEN;
  - host-agnostic, AD-2).
  - An independent adversarial review found and this commit fixes 3 SHOULD-FIX
  - (malformed-2xx KeyError; non-atomic sidecar write that could brick future
  - syncs; compiled-vs-outputs contract contradiction vs H1/§ 7.4) + NITs
  - (missing-id update crash; empty title) — all regression-tested.
  - Verify gate: tests/factory/test_lasuite.py (round-trip against an in-memory
  - mock Wagtail: create / idempotent re-push asserting 0 remote calls /
  - update-no-duplicate / mapping-resume, + outputs-not-compiled, malformed-2xx,
  - corrupt-mapping-loud, missing-id, empty-title-falls-to-stem, config-from-env,
  - error clarity, default-opener refusal, AD-22 sidecar location + no tmp left).
  - Full atlas suite 775 passed.
  - Live Wagtail/La Suite server + credential + httpx opener bring-up DEFERRED
  - (DW-H3). Also folds in the H3 DELIVERED doc updates (epics + sprint-status).
  - Claude-Session: https://claude.ai/code/session_01FYyQvBJuXwySiaMUUYCqBZ
  - Co-authored-by: Claude <noreply@anthropic.com>

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#101`.

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #101: H3: La Suite / Wagtail REST wiki sync (FR-22(c))

## Deferred Work (DW ledger)

### DW-H3 — the live La Suite/Wagtail SERVER + credential + httpx opener bring-up (ATTENDED) — DEFERRED
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story H3, § 7.1, FR-22(c))
  summary: H3 shipped the BUILDABLE half of the CMS sync — `factory/lasuite.py`: `LaSuiteClient`
    (create/update/get/list over the Wagtail/Django REST shape) + `WikiSyncer` (idempotent
    compiled-wiki → CMS push keyed by content digest: new→create, changed→update,
    unchanged→SKIP-with-no-remote-call, § 2.1 idempotent-first), verified end-to-end against an
    IN-MEMORY mock Wagtail (push / update / idempotent re-push round-trip, mapping-resume) with NO
    network. The transport is the injected `opener` seam — package code holds NO HTTP client (AC-2,
    enforced by the no-inline-IO gate), exactly like the B5/B7/B8 dataset `refresher`/`fetcher`
    injection. The ACTUAL bring-up is attended: provision the conda-forge Wagtail + django-lasuite
    server (+ PostgreSQL/MinIO from DW-H1), mint an API token, construct the live httpx-backed
    `opener` OUTSIDE package code (a script / the C1 Dagster resource), set `LASUITE_BASE_URL` +
    `LASUITE_API_TOKEN` (host-agnostic, AD-2 — never hardcoded), and run `WikiSyncer.sync_all()`
    against the real CMS. Do NOT weaken the gate to import httpx into package code or bind a socket
    (AC-2 / NFR-12). Mirrors DW-D3-1 (live LLM backend) and DW-C1-1 (live daemon).
  evidence: `factory/lasuite.py` imports only stdlib + `.crews`/`.wiki` (no httpx — the
    no-inline-IO gate `tests/catalog/test_no_inline_io.py` is green over it); the default
    `_unconfigured_opener` raises a clear "no CMS transport injected … inject the live httpx opener
    at the attended bring-up (DW-H3)" rather than reaching for the network.
    `tests/factory/test_lasuite.py` proves the round-trip + idempotency (zero remote calls on an
    unchanged re-push) + mapping-resume against the mock opener. `resolve_lasuite_config` returns
    `None` unless BOTH env vars are set.
