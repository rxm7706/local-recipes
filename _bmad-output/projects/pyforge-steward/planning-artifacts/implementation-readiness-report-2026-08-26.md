# Steward — Unifying Strategy readiness (2026-08-26)

Gate of `spec-pyforge-unifying-strategy` after the evergreen Dream rewrite
(query plane CAP-19, lasuite retracted, Kedro/Vizro option, living vs historical).

**Question:** could a developer implement Epic 34 without inventing decisions
nothing records?

**Verdict: CONCERNS — proceed.**

CAP-1..18 are shipped. Residual is **Epic 34 / CAP-19**. Story **34.1** has a
tracked spec and defaults for the three open questions. None of the concerns
block 34.1.

## Concerns (do not invent; do not block 34.1)

| Concern | Where | Why it does not block 34.1 |
|---|---|---|
| `query-plane-face` unanswered | SPEC OQ | Default: in-process DuckDB. Mosaic is later. |
| `query-plane-catalog` unanswered | SPEC OQ | Default: named new pipeline — **34.2**. |
| `query-plane-scribe-cutover` unanswered | SPEC OQ | **34.5**. Store port, not a `GraphStore` class. |
| Story **12.9** ledger `done` vs AD-11 honesty | Grounding | Optional CI. Not a stamp gate. |
| Isolated `mfa` sqlmigrate still fake | CAP-9 leftover | Not Epic 34. |
| `django-lasuite` still in `pixi.toml` | unused pin | Host does not import it. Drop is hygiene, not 34.1. |
| Bind-now pins unwired | `stack.md` | Not Epic 34 except Kedro on 34.2. |

## Trace

| Intent | Story | Spec |
|---|---|---|
| FR-46 live attach | 34.1 | `spec-34-1-read-only-live-attach.md` |
| FR-47 Parquet cache | 34.2 | write at dispatch |
| FR-48 vectors | 34.3 | write at dispatch |
| FR-49 agent OLTP shield | 34.4 | write at dispatch |
| FR-50 Scribe on plane | 34.5 | write at dispatch |

Architecture: canopy **AD-22**. No UX artifact required (no new Lane 2 chrome).

## First dispatch

`bmad-build` + `spec-34-1-read-only-live-attach.md`.
`BMAD_ACTIVE_PROJECT=pyforge-steward`. Physical paths only.

Do not re-dispatch steward 18–33.
