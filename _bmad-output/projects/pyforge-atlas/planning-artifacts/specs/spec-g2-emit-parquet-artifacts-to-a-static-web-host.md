---
title: 'Story G2 (8.2): Emit Parquet artifacts to a static web host'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #97 body + main commit log; dev narrative recovered, review-triage partial)'
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
> at `../../spec-archive/retro-story-files/8-2-g2.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story G2 (8.2): Emit Parquet artifacts to a static web host

As a dashboard consumer,
I want Parquet artifacts published to a static host and pulled via HTTP Range,
So that the WASM runtime reads live data with zero backend.

**Acceptance Criteria:** (spec § 9 Story G2, binding)

**Given** the G1 WASM runtime
**When** the emitter publishes
**Then** Parquet artifacts are published to the static host (Q4 default: GitHub Pages) and consumed by the WASM runtime via HTTP Range
**And** the emitter is host-agnostic so an enterprise mirror can substitute (Q4)
**And** the published artifact layout (chunking, manifest) has a single owner: this emitter (Spine convention).

- **FRs:** FR-14.
- **Invariants:** AD-21, AD-2 (mirror substitution).
- **Mode:** ATTENDED (publish boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q4** (WASM artifact host) — § 11 default adopted: GitHub Pages public path; emitter host-agnostic.
- **Verify gate:** **consumes `wasm-smoke`** (against the published artifact at the attended event; fixture-hosted in-loop).
- **Depends on:** G1.

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] Parquet artifacts are published to the static host (Q4 default: GitHub Pages) and consumed by the WASM runtime via HTTP Range
- [x] the emitter is host-agnostic so an enterprise mirror can substitute (Q4)
- [x] the published artifact layout (chunking, manifest) has a single owner: this emitter (Spine convention).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-14.
- **Invariants:** AD-21, AD-2 (mirror substitution).
- **Mode:** ATTENDED (publish boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q4** (WASM artifact host) — § 11 default adopted: GitHub Pages public path; emitter host-agnostic.
- **Verify gate:** **consumes `wasm-smoke`** (against the published artifact at the attended event; fixture-hosted in-loop).
- **Depends on:** G1.

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #97). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**Host-agnostic means the host is absent from the code, not parameterized in it (AD-2).**
`emit_static_site()` writes the layout to a **target filesystem path** — "the static host
filesystem." *Which* host serves it (GitHub Pages, an enterprise mirror) is a deploy choice.
No host URL and no `github.io` appears anywhere in the emit logic. The gate proves this by
serving the **same directory under two different bases** and asserting identical behavior.

**The gate proves Range consumption, not merely reachability.** `publish-range` emits the
layout to a tmp dir, serves it over a Range-capable loopback host, points a DuckDB `httpfs`
client at it, and asserts:
- consumption is **206 Partial Content reading strictly fewer bytes than the whole file** —
  a whole-file `200` **fails**. This is the actual claim: the browser pulls chunks, not the
  dataset.
- the chunk path is discovered **from the manifest** and matches its checksums (so the
  manifest is load-bearing, not decorative),
- the D1 `ci_red` result is correct **over the range-served Parquet**,
- plus determinism and the edge cases: empty, multi-chunk, corruption, past-EOF, and
  non-Range fallback.

**Skip-to-green closed here too.** `PUBLISH_RANGE_REQUIRED=1` is set on the authoritative
task so an unprovisioned `httpfs` **fails** instead of skipping — the same Reviewer-A finding
as G1. Ad-hoc local runs use bare pytest and may skip.

**A recorded inconsistency worth carrying forward.** The manifest scheme and the
`manifest.json` contract are defined exactly once, in the emitter — but **the G1 `wasm/`
runtime is not yet a manifest consumer.** G1 shipped before this emitter and built its own,
second, independent layout. The single-owner invariant holds for the emitter and its gate;
it does *not* yet hold across G1 and G2. This is stated in the module docstring rather than
papered over, and it is the natural first task if the WASM surface is taken further.

**The emitted directory is a build product** — reproducible from the emitter, gitignored,
never committed. The live publish is the attended boundary event, deferred as DW-G2.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-G2]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-G2]
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
| Pull request | **#97** — story(G2): host-agnostic static-host Parquet emitter + HTTP-Range gate (FR-14) |
| Merged | 2026-07-18 |
| Diff | 7 files, +805 / -0 |
| Test files touched | 2 |

**Commits**

- `6146f83` story(G2): host-agnostic static-host Parquet emitter + HTTP-Range gat…
- `33b3fd8` story(G2): reject over-long dataset names up front (independent revie…

**File list** *(exact, from the merged diff)*

```
  452 +     0 -  src/shared/packages/pyforge-atlas/tests/publish/test_emit_range.py
  227 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/publish/emitter.py
   68 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/publish/__main__.py
   42 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/publish/__init__.py
   13 +     0 -  pixi.toml
    3 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/publish/.gitignore
    0 +     0 -  src/shared/packages/pyforge-atlas/tests/publish/__init__.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `6146f83`** — story(G2): host-agnostic static-host Parquet emitter + HTTP-Range gate (FR-14)
  - Adds publish/ — the SINGLE OWNER of the published-artifact layout (chunked
  - Parquet + a manifest.json contract, defined once). emit_static_site writes the
  - layout to a target DIRECTORY ('the static host filesystem'); WHICH host serves
  - it (GitHub Pages public path, or an enterprise/JFrog mirror) is a deploy/config
  - choice — NO host URL / github.io is baked into the emit logic (AD-2 mirror
  - substitution; a consumer composes chunk URLs from a runtime base via chunk_url).
  - publish-range gate (tests/publish): emits the layout, serves it over a
  - Range-capable loopback host, points a DuckDB httpfs client at it, and PROVES
  - consumption is via HTTP RANGE — 206 Partial Content reading strictly FEWER bytes
  - than the whole file (measured ~2.9%); a whole-file 200 FAILs the gate
  - (non-hollow). Also asserts the chunk path is discovered FROM the manifest +
  - matches its checksums, host-agnosticism (same dir, two bases), and the D1 ci_red
  - result over the range-served Parquet. httpfs LOADed OFFLINE from cache.
  - Reviewer fixes:
  - - MUST-FIX (Reviewer-B): a dataset NAME is joined onto target_dir and rmtree'd
  - on re-emit — an unsanitized '../x' / 'a/b' / leading-slash name would delete a
  - directory OUTSIDE target_dir. _require_safe_name now rejects any traversal/
  - separator, and ALL names+types validate UP FRONT before any filesystem
  - mutation (also fixes the non-atomic partial-emit that destroyed a prior good
  - site on a late failure). Regression tests for both.
  - - Reviewer-A: publish-range pixi task sets PUBLISH_RANGE_REQUIRED=1 so the
  - authoritative gate FAILs (never skips-to-green) if httpfs is unprovisioned;
  - the single-owner docstring corrected — G1's wasm/ runtime is NOT yet a
  - manifest consumer (it fetches a flat parquet), recorded DW-G2-2.
  - DEFERRED: the live GitHub Pages publish (DW-G2-1, attended) + migrating G1 to
  - consume the manifest (DW-G2-2). 695 passed (+12).

## Review Triage Log

Independent/Gemini review produced follow-up fix commit(s) on PR `#97`:

- `33b3fd8` — story(G2): reject over-long dataset names up front (independent review, LOW)

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #97: story(G2): host-agnostic static-host Parquet emitter + HTTP-Range gate (FR-14)

## Deferred Work (DW ledger)

### DW-G2-1 — the LIVE GitHub Pages publish is the ATTENDED boundary event (not automated)
- source_spec: `g2-emit-parquet-artifacts-to-a-static-web-host.md`
  summary: G2 ships the host-agnostic EMITTER (`pyforge.atlas.publish.emit_static_site`) — it
    writes the chunked-Parquet + single-owner `manifest.json` LAYOUT to a target directory ("the
    static host filesystem"), and the `publish-range` gate PROVES that layout is consumed via HTTP
    Range (206 partial reads, footer + row groups only) by a DuckDB httpfs client over a loopback
    host. What is DEFERRED is the LIVE publish: pushing the emitted directory to a real static host
    (Q4 default: GitHub Pages `gh-pages` / an enterprise mirror) is one of the five § 2.5 ATTENDED
    boundary events — it needs credentials + a chosen host + a human at the wheel, so it is never
    run in-loop. The emitter is host-agnostic by construction (target is a PATH; the base URL is a
    runtime arg to `chunk_url`, no `github.io` anywhere in the emit logic — AD-2), so the attended
    step is purely "serve/push this directory" with zero code change to substitute a mirror.
    Wiring the browser G1 page to consume the emitted manifest layout over Range (today it fetches
    a single whole Parquet via `fetch().arrayBuffer()`) is the same attended event's follow-on.
  evidence: `src/pyforge/atlas/publish/emitter.py` (`emit_static_site` writes to a dir, relative
    manifest paths, `chunk_url(base_url, path)` composes the runtime host); `python -m
    pyforge.atlas.publish` emits to a gitignored `_site/`; `tests/publish/test_emit_range.py`
    fixture-hosts on loopback and asserts NO live publish. No push/credential/host code exists.

### DW-G2-2 — DuckDB `httpfs` must be provisioned once (offline-LOAD in the Range gate)
- source_spec: `g2-emit-parquet-artifacts-to-a-static-web-host.md`
  summary: The `publish-range` gate's Range consumer is a native DuckDB `httpfs` client (the same
    engine + Range mechanism DuckDB-WASM uses in the browser). Like `vss` (DW-F3-2), DuckDB's
    default `INSTALL httpfs` hits the network, which collides with the offline invariant — so the
    gate LOADs httpfs from the local extension cache with autoinstall/autoload DISABLED. If httpfs
    is not provisioned, the gate SKIPS locally with the provisioning step named (a legitimate
    not-provisioned skip, DISTINCT from the range-read-actually-failed case, which always FAILS),
    and under CI / `PUBLISH_RANGE_REQUIRED=1` it FAILS instead of passing having verified nothing.
    A fresh air-gapped/CI environment must run `INSTALL httpfs;` once (attended, network) to
    populate the cache before the gate can run offline — mirrors the vss provisioning story.
  evidence: `tests/publish/test_emit_range.py::_offline_httpfs_connection` (autoinstall/autoload
    off → LOAD-from-cache → skip-or-fail on failure, `_publish_required()`); the container's cache
    already carries `httpfs.duckdb_extension` (v1.5.4) so the gate runs GREEN here.

### DW-G2-2 — migrate the G1 wasm/ runtime to consume the emitter's manifest (single-owner completion)
- source_spec: `g2-emit-parquet-artifacts-to-a-static-web-host.md`
  summary: G2's emitter is the single owner of the PUBLISHED-site layout (chunked Parquet +
    manifest.json), READ by the publish Range gate. But G1's wasm/ runtime shipped first and
    fetches a FLAT `./core_feedstock_health.parquet` (its own build.py produces that flat file) —
    it does NOT read manifest.json / chunk_url yet, so it is a SECOND, independent layout for the
    same data (Reviewer-A). Completing the single-owner invariant = migrating G1's index.html to
    load the manifest + compose chunk URLs via chunk_url (and having build.py emit via the
    emitter). Deferred because it re-touches the G1 WASM artifact + its ~41 MB bundle rebuild
    (DW-G1-2 CI build step) and is best done with the live-publish bring-up (DW-G2-1). Until then
    the emitter/gate own the published layout; G1 remains an independent dev artifact.
  evidence: `wasm/index.html` hardcodes `fetch("./core_feedstock_health.parquet")`;
    `wasm/build.py::_csv_to_parquet` produces the flat file; the emitter produces
    `core_feedstock_health/core_feedstock_health-0000.parquet` + `manifest.json`. The publish gate
    IS a manifest consumer (proves the layout); G1 is not yet.
