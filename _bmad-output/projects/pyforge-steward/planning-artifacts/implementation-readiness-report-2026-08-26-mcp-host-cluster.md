# Steward — mcp-host cluster required readiness (2026-08-26)

Gate of `spec-mcp-era-isolation` CAP-4 after the operator asked to enforce
the MCP bridge on the cluster without mixing it into Epic 34.

**Question:** could a developer implement 35.1 without inventing decisions?

**Verdict: CONCERNS — proceed.**

Slice 1 is shipped. Residual is **fail-loud omission** (Helm + production
check + docs). Slice 3 stays parked. Epic 34 is a different queue.

## Concerns (do not invent; do not block 35.1)

| Concern | Where | Why it does not block 35.1 |
|---|---|---|
| Chart already always emits mcp-host | `cluster-required.md` | Story hardens empty-image / no-`enabled` / Django check |
| Slice 3 skip still present | `retire-skip.md` | Required until pins converge |
| CRC pods not re-probed | operator session | 35.1 is template + check tests; not a 12.7 re-prove |
| Epic 34 still first dispatch | unifying readiness | Serial sessions; 35.1 has **deps: none** |

## Trace

| Intent | Story | Spec |
|---|---|---|
| CAP-4 cluster cannot omit mcp-host | 35.1 | `spec-35-1-cluster-requires-mcp-host.md` |

## Dispatch order

1. `bmad-build` + `spec-34-1-read-only-live-attach.md`
2. Then `bmad-build` + `spec-35-1-cluster-requires-mcp-host.md`

`BMAD_ACTIVE_PROJECT=pyforge-steward`. Physical paths only.
