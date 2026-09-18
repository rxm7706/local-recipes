---
companion-of: spec-pyforge-doctor
capability: CAP-77
---

# Live-proof-only surfaces

CAP-77's catalog. Each row is a real, currently-existing surface where a dev
pass's own self-report is structurally not evidence — the only thing that
proves it is a real round-trip against something outside the repo. Every
"How to prove it live" cell names a mechanism that already exists; a surface
with none is marked so explicitly rather than left implying one exists.

| Station | Surface | Why a static/self-report pass misses it | How to prove it live | Cost |
|---|---|---|---|---|
| herald | Claude Design MCP bridge (push) | A push can succeed against a stale/broken transport and still report "done" — proven live by the 2026-09-17/18 incident: two silent `mcp` SDK 2.x breaking renames (`streamablehttp_client`→`streamable_http_client`, different call signature; `CallToolResult.isError`→`.is_error`) passed review and the test suite. | `herald deck push --prove` reads every pushed file back through Design's serve URL, strips the injected harness, asserts byte-identity. `transport/mcp_transport.py`. | One real network round-trip per pushed file; needs a live Design credential. |
| herald | Live webhook host | `webhook_host.py`'s ASGI wiring can be structurally correct and still never actually accept a real signed request. | `HERALD_LIVE_WEBHOOK=1` opt-in; `.github/workflows/herald-live-demo.yml` starts a real `daphne` process and `test_webhook_live_smoke.py` sends a real signed HTTP POST over loopback. | Opt-in only, never in the default gate — a real subprocess + real socket. |
| herald | PPTX export needs a real Chrome/Chromium | A missing browser is an environment fact, not something the code alone proves. | `chrome_available()` (`scripts/deck_export.py`) checks for a real binary before the `--pptx` targets run; skips with a named reason instead of crashing when absent (Story 23.3). | Cheap (a binary-existence check) — already solved, listed as the pattern the other rows should match. |
| scribe | Postgres+pgvector cluster | Scribe's tests read/write a real database; a mock passes without proving the real schema or the vector extension work. | `scribe-pg-up` starts the local cluster first. "CI has a service container" is not a substitute for running this locally before trusting a red suite. | A real local Postgres process; not covered by `pr-preflight`. |
| atlas | Chromium/DuckDB/WASM pipeline | The pipeline's own correctness depends on a real headless-browser render and a real DuckDB/WASM runtime, neither reproducible from static review. | No single documented live-proof command as of this writing — **named gap, not a fabricated mechanism.** | Unknown; needs atlas's own scoping before a Doctor finding can cite a concrete proof step. |
| warden | Live OSV-scanner / CISA-KEV / EPSS feeds | A compliance verdict is only as current as the live feed it queried; a stale local cache can pass while the real upstream data has moved. | `warden scan` queries the live feeds directly at scan time — the proof IS the scan, not a separate step. | Live network calls per scan; rate-limited by the upstream services. |
| guild (cross-station) | `guild-container` / `container` (docker, podman) | An image can build and even run locally while still being broken in the actual container runtime path the fleet ships through. | `pixi run -e <env> container` / `guild-container` build+run tasks (docker and podman variants both exist). | Needs a real Docker or podman daemon; not covered by `pr-preflight`. |

## Reference pattern already solved elsewhere in this Spec

CAP-14 (installed-vs-upstream `bmad-method` drift) already does the thing
every row above should imitate for its own finding: a live query (npm
registry) that degrades silently and fails open when offline or unreachable,
never blocking or failing the check-suite on the network call alone
(CAP-15). A CAP-77 finding for any row above should follow this same
fail-open discipline once implemented — never treat "couldn't reach the live
surface" as itself a fail.
