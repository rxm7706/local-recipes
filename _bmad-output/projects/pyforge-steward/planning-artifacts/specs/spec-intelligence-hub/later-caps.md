---
doc: later-caps
spec: intelligence-hub
status: parked
updated: 2026-09-14
---

# Adopt-anytime later-caps — not Launch, not Non-goals

Moved out of `SPEC.md` Non-goals on **2026-09-13 (D4)**. These **may land before or
after 44.3**. They are not forbidden. They are **not** the Launch campaign
(Hub CAP-1..4 + first nine Frames + Track + Guards).

Mint a Story (and hoist into `SPEC.md` via memlog / `bmad-spec`) before writing
code. CAP-5 (package NIC locally) stays the **mason** lane — green local build,
no external PR — do not mint mason stories on steward Epic 53.

| ID | Item | Why later | Gate |
|---|---|---|---|
| **LC-1** | Community Frame | B9 first nine Frames are Company + 8 stations in git | none beyond CAP-2 preflight if authored |
| **LC-2** | Frame registry | B9 git store first; registry was a hard ban until D4 | not a fourth infra kind without an ask |
| **LC-3** | Skills / Agent Marketplace | was bundled with Desktop/Web Application Non-goal; **sibling Dream** [`docs/dreams/self-hosted-bmad-marketplace.md`](../../../../../../docs/dreams/self-hosted-bmad-marketplace.md) (2026-09-14) owns the BMAD catalog SKU — do not collapse with Frames or Layer 3 | Desktop/Web Application stays a Non-goal; do not hoist into Hub Launch without an ask |
| **LC-4** | NIC as substrate (align reading 3) | D-1 reading 2 is Launch | first green `ocp-portability-smoke` before a NIC **kind profile** (Constraint) |
| **LC-5** | Semantic-as-default | Scribe default recall stays lexical; unifying CAP-14 is steward 49.7 | do not flip Scribe default |
| **LC-6** | Wholesale `docs/` / `recipes/` in the Scribe graph | named extras only (Scribe Epics 14–15) | do not nightly-graphify `recipes/` or repo root |
| **LC-7** | `NebariApp` template | D-2 / D4 — not Launch | chart Ingress/Route stays primary (`pap:AD-11`) |
| **LC-8** | `nebi push` of station workspaces | D-3 / D4 — not Launch | still not before operator ask |

**Still Non-goals (D2/D4 keep):** no replace Foundry with Nebari; no replace
`conda-forge-expert`; no endorse/marketing OpenTeams; no reproduce the
whitepaper; no conda-forge PRs for NIC/frames.
