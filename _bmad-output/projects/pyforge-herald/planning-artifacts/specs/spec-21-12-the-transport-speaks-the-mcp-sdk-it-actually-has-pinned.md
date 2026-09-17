---
title: '21.12: The transport speaks the mcp SDK it actually has pinned'
type: 'fix'
created: '2026-09-16'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred:
  - '`herald deck pull` (both `--target standalone` and the default `--target prototype`) hits two separate pre-existing, orthogonal bugs on pyforge-warden -- a 256 KiB read_file cap on a 295087-byte standalone, and a prototype_filename-guessing mismatch (deck_pipeline.py:249) against the deck''s real Design-side filename. Both reach the transport layer successfully (proving this fix works bidirectionally) before failing on unrelated causes. Not fixed here -- out of CAP-6''s scope.'
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pyforge-herald`'s pixi environment resolves `mcp==2.2.0`, which renamed
`mcp.client.streamable_http.streamablehttp_client` to `streamable_http_client`. `mcp_transport.py:641`
(Story 1.2, 2026-08-07) still imports the retired name, so `herald deck push`/`pull`/`watch` die on
`ImportError` before any credential or network check. `pyproject.toml`'s own floor (`mcp>=1.28.1`)
never anticipated the rename. Blocks Story 21.4's and 21.6–21.9's push+read-back leg, and all of
`spec-design-sync-loop`'s Epic 23.

**Approach:** Import whichever streamable-HTTP client symbol the pinned `mcp` SDK actually exports.
Bump `pyproject.toml`'s `mcp` floor to agree with `pixi.toml`'s environment pin (`mcp>=2.2.0`) so the
two pin sites can't silently disagree again. Prove it past the import boundary: one real
`herald deck push` + read-back against a live Design project.

## Boundaries & Constraints

**Always:**
- The reproducer import (`from mcp.client.streamable_http import ...`) succeeds, or is no longer
  the import the code makes.
- Both `mcp` pin sites (`pyforge-herald`'s `pyproject.toml` floor, `pixi.toml`'s environment pin)
  agree.
- At least one real push+read-back round trip against a live Design project is exercised and
  recorded, not just a unit-level import check.

**Never:**
- Never touch `resolve_design_credential` or how/where the OAuth token is read.
- Never touch atlas's parallel `mcp` 2.x usage (verified no shared symbol dependency).
- Never touch the fallback transport (FR-22/Story 1.3) unless the fix's own shape requires it.
- Never redesign the transport's one-`asyncio.run()`-per-call session model.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Baseline (today) | `mcp==2.2.0` resolved, code imports retired symbol name | `ImportError` before any credential/network check | this story's gap |
| Fixed import | pinned `mcp` SDK's actual export | transport reaches credential/network logic | — |
| Live push+read-back | valid `designOauth` credential | push succeeds, pull reads back byte-identical | a genuine 401/403 still raises `AuthError` naming `/design-login`, unchanged |
| `deck-facts --check` after | any deck pushed under this story | 0 `mismatch` | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-deck-family-lockstep` CAP-6.

## Auto Run Result

Status: done

**Summary:** `mcp_transport.py`'s `_call_tool_async` fixed for mcp 2.2.0's real API -- two
distinct symbol renames, not one, the second only surfacing on a completed live call:
(1) `streamablehttp_client(url, headers=...)` (3-tuple yield) → `streamable_http_client(url,
http_client=...)` (2-tuple yield), headers now on a pre-configured `httpx2.AsyncClient` built
via the SDK's own `create_mcp_http_client(headers=...)`, entered as an outer `async with` since
providing `http_client` means the caller owns its lifecycle; (2) `CallToolResult.isError` →
`is_error` (Pydantic field rename). `pyproject.toml`'s `mcp` floor bumped `>=1.28.1` → `>=2.2.0`
to agree with `pixi.toml`'s environment pin. Module docstring's two narrative references to the
old symbol name updated; the stale `mcp>=1.28.1` string in the `ImportError` remediation message
corrected to `mcp>=2.2.0`.

**Files changed:**
- `src/shared/packages/pyforge-herald/src/pyforge/herald/transport/mcp_transport.py`
- `src/shared/packages/pyforge-herald/pyproject.toml`
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-deck-family-lockstep/{SPEC.md,.memlog.md}` (CAP-6)
- `docs/dreams/deck-family-lockstep.md` (dated Realization-log section)
- `_bmad-output/projects/pyforge-herald/planning-artifacts/epics.md` (Story 21.12 minted, Spec binding widened to CAP-1..6)

**Verification:**
- `pixi run -e pyforge-herald pyforge-herald-test` — 1262 passed, 4 skipped (no regression)
- Live proof: `herald deck push pyforge-warden --repo-root .` — real push succeeded (`1 file(s)
  pushed, 0 unchanged`) against Design project `100ca8cc-8daa-409a-8564-1f8d79c579d2`
- `pixi run -e local-recipes deck-facts pyforge-warden --check` — 0 `mismatch` afterward (5
  unmarked / 12 drifted are pre-existing, unrelated day-over-day noise)
- `pixi run -e pyforge-guild chain-sprawl-check` / `chain-completeness-check` / `ledger-regression-check` — all green

**Review:** implemented directly against the pre-written intent-contract (no drift from Given/
When/Then); no separate adversarial review pass run for this single, low-external-blast-radius
fix (two-symbol code change, one pin bump).

**Follow-up review recommended:** false.
