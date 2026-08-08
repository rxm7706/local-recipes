# Dream triage — 10 backlog Specs, 2026-08-08

10 Dreams that were flagged by `dream_chain_check.py` (INV-1: every Dream needs a Spec) now
each have a real `status: draft` Spec — see each `spec-<slug>/SPEC.md` for the full contract.
None of this is built. This doc is the one-page decision aid: fold into a station's real
epics, or archive as not-going-to-implement. **The call is the operator's**, not a
recommendation this doc makes for you — it summarizes each Spec's own readiness signal.

Detector state after all 10 Specs landed: `OK: all three invariants hold` (0 findings, was 16).

## How to read the columns

- **Scope** — rough size signal from the Spec itself (capability count, LOC/file counts where
  named).
- **Readiness signal** — what the Spec's own Constraints/Open-Questions say about whether it's
  ready to fold in as-is, or needs a decision/rescoping first. Not a recommendation — a summary.
- **If folding in** — which station and roughly where (existing epic vs. new epic), per the
  Spec's own `owner-dream:`/surface.

---

| # | Dream | Station | Scope | Readiness signal | If folding in |
|---|---|---|---|---|---|
| 1 | `loop-home-fleet-refresh` | Marshal | 3 capabilities (staleness detection, FF+push, policy re-render) | **Ready** — grounded in this session's own lived pain (9 worktrees, 227 commits stale, hand-run twice today); no open question blocks scoping | New epic or extends `marshal homes`/`init`/`preflight`; Q1 (verb vs. cron vs. both) is the only real decision left |
| 2 | `dashboard-project-path-derivation` | Marshal | 4 capabilities, single-file surface (`docs/dashboard/generate.py`) | **Ready** — a TODO already sits in the code (`generate.py:42`) naming this exact gap; edge cases (regen/genesis/CI) already verified against the live code | Small, contained story against `docs/dashboard/generate.py`; doesn't need a new epic, could be a maintenance PR |
| 3 | `unified-container` | Steward | ~4-6 stories per Steward's own feasibility research | **Ready, but big** — real blockers already named (checkout-anchoring, AD-1 distroless-off-the-table, flock-not-over-NFS) with a Podman-secrets credential path already worked out | New epic; sequencing note: `bmad-module-provisioning` (below) should probably land first if you want `provision --module` inside the same image build |
| 4 | `kedro-org-tooling-adoption` | Atlas | 3 capabilities, explicitly scoped as **audit-and-decide**, not adoption | **Ready, small** — deliberately narrow (audit `kedro-skills` v0.1.1 against AD-invariants; pick a Kedro-Viz publish mechanism; record an adopt/defer call on `vscode-kedro`) | Single small story or spike, not an epic; time-sensitive since `kedro-skills` is one day old as of this Spec |
| 5 | `dream-to-code-model-self-verification` | Marshal | 4 capabilities (meta-tests for the 2 detectors, an incident log, `--dreams` hygiene mode) | **Ready** — this session's own satellite-consolidation detector bug (fixed today, commit `e3171bdcc6`) is now the first entry in the incident log this Spec proposes | New epic or a tooling/meta story; lowest urgency of the "ready" group — pays off over time, not immediately |
| 6 | `bmad-module-provisioning` | Steward | 1 new `provision` backend (subprocess wrap of BMB/Skill-Forge installers) | **Ready** — Terraform-style "add a backend, not a state file" pattern already matches Steward's existing 2-backend `ProvisionDuty` shape | Extends the existing `provision` epic; natural predecessor to `unified-container` if you want modules provisioned inside the image build |
| 7 | `sprint-status-auto-promote` | Marshal | 4 capabilities (mechanical trigger, drift detector, no-heuristics constraint, single-writer race guard) | **Needs one decision** — the trigger mechanism (hook vs. standing check-in step vs. both) is Q1 and genuinely undecided; everything else is scoped | Small-to-medium story once Q1 is picked; low risk either way |
| 8 | `herald-moments-2-4-live-backend` | Herald | 3 capabilities (real DB, webhook, cron) — the full deferred live-backend | **Archive-leaning** — the Spec's own first open question is literally "is this worth building at all," and names a hard prerequisite (replace `state.py`'s unlocked read-modify-write) that blocks it regardless; CLI-triggered v1 has already proven adequate | If folded in: NOT a story, a new multi-epic effort — do not attempt without first resolving the concurrency-lock prerequisite |
| 9 | `jira-github-projects-sync` | Marshal | 5 capabilities, greenfield (confirmed via grep — nothing exists today) | **Needs a decision, not more scoping** — 5 open questions (Q1-Q5: which external system, which side is authoritative, Mode A vs B, marshal-vs-steward ownership) that only the operator can answer; more research won't resolve them | Don't fold in yet — answer Q1-Q5 first, or archive if there's no real external Jira/board this repo needs to sync with |
| 10 | `conda-forge-expert-rebuild` | Mason | Deliberately NOT the whole skill — Spec scopes to 1 first slice (recipe generation) of ~41K LOC / 67 scripts | **Needs rescoping or archive** — the Spec's own open questions ask whether this is even Mason's to own (vs. Atlas's intelligence tier) and whether Skill-Forge's `skf-create-skill` can drive code-scale compilation at all, not just knowledge-layer content | If folded in: pilot the ONE slice (recipe generation) as a spike first, with an explicit re-scope gate after — do not commit to the full rebuild up front |

## Summary by lean

- **Ready to fold in as scoped (6):** loop-home-fleet-refresh, dashboard-project-path-derivation,
  unified-container, kedro-org-tooling-adoption, dream-to-code-model-self-verification,
  bmad-module-provisioning
- **Ready pending one decision (1):** sprint-status-auto-promote (pick the trigger mechanism)
- **Archive-leaning (1):** herald-moments-2-4-live-backend (its own Spec questions the premise)
- **Needs an operator decision before any more work (2):** jira-github-projects-sync (which
  system, which direction), conda-forge-expert-rebuild (whose it is, whether it's even feasible
  at code-scale)

## Suggested sequencing if folding in the "ready" group

A natural dependency order, not a mandate:

1. `dashboard-project-path-derivation` — smallest, no dependencies, closes a code TODO.
2. `kedro-org-tooling-adoption` — small, time-sensitive (the kedro-skills package is one day old).
3. `bmad-module-provisioning` — feeds into `unified-container`.
4. `unified-container` — the biggest of the "ready" group; benefits from #3 landing first.
5. `loop-home-fleet-refresh` — independent, can run in parallel with any of the above.
6. `dream-to-code-model-self-verification` — lowest urgency, pays off over time.
