---
title: 'Story H3 (9.3): Integrate La Suite Docs REST API Sync'
type: 'feature'
status: 'regenerated'
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

### Story H4 (9.4): Orchestrate Crews via Dagster

As the operator,
I want Dagster assets, sensors (new raw files), and schedules (weekly linting) triggering the Agno crews autonomously,
So that the factory layer runs itself.

**Acceptance Criteria:** (spec § 9 Story H4, binding)

**Given** the H2 crews and the C1 Dagster repository
**When** the assets/sensors/schedules land
**Then** an asset dry-run enumerates the crew assets
**And** a simulated new-raw-file event triggers the compile crew via a Sensor.

- **FRs:** FR-22(d), FR-6.
- **Invariants:** AD-22, AD-6, AD-23.
- **Mode:** LOOP-E (spec § 9 explicit).
- **Gating question:** none.
- **Verify gate:** `dagster-dryrun` (crew assets enumerate) + simulated-trigger fixture.
- **Depends on:** H1, H2, H3; C1.
- **DELIVERED (2026-07-18 — closes Wave H + the migration):** the Wave-H crews run on C1's single Dagster plane (AD-6/AD-23). `orchestration/definitions.py` gains crew ASSETS (`compiled_wiki` → CompileCrew, `wiki_lint_report` → LintCrew, `deps=[compiled_wiki]`), their asset-jobs (`wiki_compile_job`/`wiki_lint_job`), a weekly LINT schedule (`wiki_lint_schedule`, `0 6 * * 1`, § 7.2), and the new-raw-file compile SENSOR (`wiki_raw_file_sensor` → `wiki_compile_job`, ships STOPPED). The raw-scan + cursor-dedupe DECISION logic lives in `orchestration/wiki_events.py` (dagster-free — AD-1 holds; only definitions.py imports dagster). `dagster definitions validate` green; a simulated new-raw-file event (injected lister + `build_sensor_context`) → one `RunRequest` for the compile job. Live daemon + wiki-store bring-up DEFERRED (DW-H4). Gate `test_definitions_dryrun.py` H4 section (+12; C1/G3 invariants scoped to kedro op-jobs via `_kedro_jobs`). Independent review found 1 SHOULD-FIX (`_decode_cursor` crashed on a valid-JSON-but-nested cursor, breaking its "never a crash" contract) — fixed (filter to str inside the guard) + regression-tested; the `_kedro_jobs` scoping was verified NOT to weaken any C1/G3 guard.

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

## Dev narrative — recovered from the merged record (2026-07-25)

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #101: H3: La Suite / Wagtail REST wiki sync (FR-22(c))

## Story H3 — Integrate La Suite Docs REST API Sync (FR-22(c), § 7.1)

Pushes the Karpathy wiki's final report pages up to the Layer-1 Wagtail/La Suite CMS. `factory/lasuite.py` imports stdlib + `.crews`/`.wiki` only — no HTTP client in package code (AC-2 no-inline-IO gate green).

### Changes
- **`LaSuiteClient`** — create/update/get/list documents over the Wagtail/Django REST shape. Owns base URL + bearer auth; delegates the wire to an **injected `opener`** (the sole network seam, like the B5/B7/B8 dataset fetcher injection). Non-2xx **and** a malformed 2xx-without-`id` both become a clear `LaSuiteError` (§ 2.1). The default opener refuses (no transport injected) rather than importing httpx — the live opener is the attended bring-up (DW-H3).
- **`WikiSyncer`** — idempotent `outputs/` → CMS push keyed by content digest. Reads `wiki/outputs/` by default (the Oracle's **final reports** for the human CMS, per the H1 layout contract + § 7.4 — not the internal `compiled/` stage; `source_stage` overrides). Mapping (`<wiki-root>/.lasuite_sync.json`) records CMS id + last-synced sha: new→create, changed→update (no duplicate create), unchanged→**skip with zero remote calls** (§ 2.1). Mapping lives at the wiki ROOT (AD-22), written **atomically** (tmp + `os.replace`), and a corrupt mapping fails **loudly** on load (never silently empty).

### Independent review
An adversarial fresh-eyes review found **3 SHOULD-FIX** (malformed-2xx `KeyError`; non-atomic sidecar write that could brick future syncs; `compiled`-vs-`outputs` contract contradiction vs H1/§ 7.4) + 2 NITs (missing-id update crash; empty title) — **all fixed and regression-tested** in this PR.

### Deferred
- Live Wagtail/La Suite server + credential + httpx opener bring-up → **DW-H3**.

### Verification
- `tests/factory/test_lasuite.py`: round-trip against an in-memory mock Wagtail (create / idempotent re-push asserting **0 remote calls** / update-no-duplicate / mapping-resume) + the 5 review-regression tests.
- Full atlas suite: **775 passed**. AC-2 / AD-1 gates green.

### Commits on `main`

- `4d680b09c1` H3: La Suite / Wagtail REST wiki sync (FR-22(c)) (#101)  _(dev-landing)_

_This PR also carried an automated Gemini review; not reproduced here per repo policy ([[feedback_no_gemini_reviews]])._

