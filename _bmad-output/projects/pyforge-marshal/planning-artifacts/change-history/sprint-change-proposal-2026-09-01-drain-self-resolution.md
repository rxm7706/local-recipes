---
date: 2026-09-01
trigger: docs/dreams/marshal-dependency-aware-dispatch.md
kind: fold-in
---

# Sprint Change Proposal — Drain self-resolution (addendum F)

## Why

2026-09-01 fleet `drain_to_zero` still required a chat session after Epic 28
stories 28.12–28.17 shipped. Residual is named in Dream addendum F.

## Adjustment

**Direct** — append Stories **28.18–28.23** to Epic 28; kernel
`spec-marshal-drain-self-resolution` status `ready`; six tracked story specs
`status: ready`; ledger backlog; queue order 28.18 → 19 → 21 → 20 → 22 → 23.

**v1 locks:** no auto-authored stub spec; cheap re-preflight; local-clean land
when GitHub `DIRTY`; blast radius in verify.

**Archive:** `docs/dreams/marshal-drain-self-resolution.md` is a pointer only.

## Out of scope

Loop-home ff-merge. Auto-draft specs. Replacing 28.13 / 28.17.
