---
title: 'Wire compression at the harness seam (Story 28.2, Epic 28)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: heavy
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/integration-layers.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings:
  - headroom-ai is ACTIVE in pixi since 2026-08-30 (0.37.0, all platforms — the
    pixi-candidate-currency click wall fell; `headroom` CLI verified live). The seam must
    STILL be fully testable with an injectable wrapper and degrade gracefully when the
    instrument is absent (non-linux fleets, future regressions) — availability changed,
    the design constraint did not.
---

<intent-contract>

## Intent

**Problem:** Every tool output, log, and file read a session makes crosses the wire
uncompressed — the dominant, unbounded per-iteration token sink. Marshal's harness profiles
launch the coding CLI bare.

**Approach:** Harness profiles gain an optional wrapper field (e.g. `headroom wrap <cli>` /
transparent proxy for base-URL-only tools), applied at spin/dispatch when the `[context]`
wire layer is enabled (Story 28.1's block). The CCR (compress-cache-retrieve) store is
loop-home-scoped, torn down with the worktree. The wrapper is injectable so the seam is
testable without the real instrument.

## Acceptance Criteria

- Given an enabled wire layer, when spin/dispatch launches a session, then the launched
  command is demonstrably wrapped (profile-resolved, journal-visible) and the CCR store path
  is inside the loop home.
- Given a compressed artifact in the CCR store, when retrieved, then it is byte-exact to the
  original.
- Given identical inputs wrapped vs unwrapped, when the provider call is composed, then the
  prompt prefix (system prompt, tool definitions, older turns) is byte-identical — proven by
  a prefix byte-comparison test.
- Given the instrument is unavailable (not installed, platform gap), when a run launches,
  then the layer disables with a named finding and the run proceeds unwrapped — never a
  blocked run, never a silent no-op.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-marshal/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Ledger
key `28-2-wire-compression-at-the-harness-seam`.

**Block If:** A change would compress the story spec/ACs/gate verdicts/escalation context,
rewrite the prompt prefix (NFR-14 violation), or wire the BSL-1.1 `@caveman-ai/cli` proxy.

**Never:** Silently-lossy compression (reversible-or-absent). A second gate verdict. Editing
`pixi.toml` to force-activate headroom-ai (that unblock belongs to pixi-candidate-currency).
Enabling headroom's cross-agent SharedContext memory feature — a second memory
store-of-record by the back door; Scribe's capture/recall (`.claude/memory/` +
`graph_store`) is the fleet's only sanctioned memory face (unifying-strategy Grounding
2026-08-30: agents do not write to a side memory instead of `scribe capture`).

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/harness_profile.py`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/data/harness_profiles/*.toml`
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` + `adapters/harness_bmadbuild.py` (launch paths)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py` + `cli/dispatch.py`

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(wrapper injection, CCR byte-exactness, prefix byte-comparison, graceful-degradation
finding). Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 28.2 and spec-marshal-token-economy CAP-2. The admission requirement
is live-zone-only compression (provider cache hot zone untouched) — headroom's documented
design; the test proves the property, not the vendor claim. Profile wrapper field follows the
harness-profile packaging convention (Story 1.10 / harness_profile.py precedent).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, including this story's own new/updated test coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (no undeclared dependency surface).

## Spec Change Log

- 2026-08-30: drafted from epics.md Epic 28 for fleet-drain preflight (Dream/Spec chain: docs/dreams/marshal-token-economy.md → spec-marshal-token-economy)
- 2026-08-30: added the Never against headroom's cross-agent SharedContext memory (second memory SoR risk; Scribe owns the memory face per the unifying-strategy Grounding)
