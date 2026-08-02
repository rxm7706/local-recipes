# Constitution provenance — the 14-Article requirement spine

Source: `docs/intake/gists/spec-kit/constitution.md` v1.2.0 (ratified 2025-11-20; next-review
2026-02-20 — already overdue). Full detail: PRD § 14 (`prds/prd-unity-data-stack-2026-07-25/prd.md`).
Every Mandate in the Constitution traces to the FR that carries it, or to its disposition below.

## Articles I–XIV — disposition

| Article | Subject | Carried by |
|---|---|---|
| I | Identity, stack, repository structure | FR-1, FR-5 |
| II | Pixi-first package management | FR-1, FR-10, FR-14, FR-27 |
| III | Spec validation (tests) | FR-20, FR-21, FR-53; **amend** for FR-25 |
| IV | Agentic quality enforcement | FR-18, FR-19, FR-22, FR-23 |
| V | Specification standards | FR-31, FR-32, FR-51 |
| VI | 12-stage SDLC | FR-9, FR-57, FR-58 |
| VII | Data mesh | FR-48–FR-52 |
| VIII | Spec-driven collaboration | FR-33–FR-36 |
| IX | Dagster best practices | FR-50, FR-51, FR-53 |
| X | Continuous spec enforcement | FR-18, FR-24, FR-32, FR-56 |
| XI | Performance and scalability | **Not carried in v1** — guidance only, no platform mechanism; candidate for demotion to a guide |
| XII | Security and compliance | FR-15, FR-16, FR-22, FR-39–FR-47, FR-57, FR-58 |
| XIII | Simplicity gate | FR-27, FR-31 |
| XIV | Python version support | **Revised** — see amendment 3 below |
| Governance | Authority, amendment, enforcement | FR-26, FR-28, FR-29, FR-30 |

## The Article II mandate table (rows sourced from several Articles)

| Mandate | Priority (as stated) | Carried by | Disposition |
|---|---|---|---|
| Local First — per-package environments, testing, docs | CRITICAL | FR-3, FR-5, FR-18, FR-59 | Adopted |
| Package Management — pixi, conda-forge, air-gap | CRITICAL | FR-1, FR-10, FR-14 | Adopted |
| Production — OpenShift + GitOps | CRITICAL | FR-56 | Adopted; version unverified (architecture AQ-1) |
| MCP — agent message transport | CRITICAL | — | Adopted. **Terminology corrected**: the Constitution expands MCP as "Multi-Agent Communication Protocol"; the correct expansion is **Model Context Protocol** |
| A2A — agent collaboration semantics | CRITICAL | — | Adopted as an integration dependency; no v1 FR |
| REST — API architecture | CRITICAL | — | Applies to Packages Unity hosts, not Unity's own surface; not an FR |
| Environments — 12-stage SDLC | CRITICAL | FR-9, FR-58 | Adopted **as Stages**, modelled separately from Environments (AD-4) |
| Orchestration — Dagster ≥1.12.0, sole platform | HIGH | FR-48–FR-53 | Adopted; floor to be re-set (1.13.15 current) |
| Data Mesh — DDD, three layers | HIGH | FR-48–FR-52 | Adopted |
| Data Science — Kedro, sole toolbox | HIGH | — | Adopted as dependency; no v1 FR |
| Web Application — Django + React, preferred | HIGH | — | Adopted as dependency; "preferred" ⇒ **Domain Default**, not Platform Invariant |
| RESTful API — FastAPI, preferred | MEDIUM | — | Same as above |

## The 8 required amendments

1. **Art. II mandate table** — classify every row as Platform Invariant or Domain Default (FR-26). "Preferred" rows are Domain Defaults by their own wording; "sole" rows are Invariants.
2. **Art. III** — add the behavioural test tier the working root already implements (FR-25).
3. **Art. XIV** — revise the Python support policy: 3.12 is security-phase upstream; 3.15 arrives 2026-10-01; the stated 2-year rule, applied literally, already expires the declared baseline.
4. **Art. XI** — demote to guidance, or supply mechanisms and requirements.
5. **Art. XII § 12.6** — either supply mechanisms for PII masking / retention / right-to-deletion, or scope them explicitly (see Spec Open Questions / OQ-8 in the PRD).
6. **Art. II MCP row** — correct the protocol expansion (Model Context Protocol, not Multi-Agent Communication Protocol).
7. **Art. VIII § 8.3** — name whose approval is required (FR-33, the Trusted Committer role).
8. **Governance § Next Review** — overdue since 2026-02-20; re-ratify alongside these amendments.

## The flagship command that does not exist

The intake toolchain spec's flagship lock-generation task is:

```
pdm export --format pylock --override-platform=linux --override-platform=macos --override-platform=windows
```

Verified 2026-07-25: **`pdm export` has no `--override-platform` flag.** Platform targeting on PDM
lives on `pdm lock --platform`; the format token is `pylock.toml`. A working alternative exists
(`uv export --format pylock.toml`), but the intake spec's exact mechanism is unimplementable as
written. Compounding this, PEP 751 itself does not guarantee multi-platform lockfiles — it uses
environment markers, not a cross-compilation guarantee — so the "Cryptographic Predictability"
outcome the intake spec promised had no verified mechanism at all. This is the empirical grounding
for AD-2 (Workspace Lock authoritative, PEP 751 export derived and drift-checked) and AD-3
(multi-platform coverage proven by materialization, never inferred) in the architecture spine.
