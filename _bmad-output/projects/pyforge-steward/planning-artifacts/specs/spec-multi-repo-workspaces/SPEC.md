---
spec: multi-repo-workspaces
status: ready   # PARKED 2026-09-09 with a named trigger — "when a second repo joins the estate",
                # i.e. Story 44.3 (python-foundry). See § Spec Change Log.
updated: "2026-09-09"
owner-dream: docs/dreams/multi-repo-workspaces.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/multi-repo-workspaces.md
open_questions: []   # The registry-location question answered itself and is retired 2026-09-09
                     # (batch row stB-C7): resolved at Story 13.3 as `.steward/repo-sets.yaml`
                     # (`workspace.py:38`). A resolution belongs in the Spec Change Log, not in a
                     # live question — the entry below is where it lives.
---

# SPEC — One workspace opens every repo a story touches

## Why
Fleet work spans local-recipes + conda-forge-tracker + feedstock clones;
workspace tooling is single-repo (Epic 13's 13.1/13.2, backlog). Decision
(memlog): EXTEND Epic 13 — this is the layer above those verbs, not a
second system.

## Capabilities
- **CAP-1 — repo sets + coordinated start.** Declarative `[projects.<slug>]`
  repo sets; `steward workspace start <feature>` cuts one worktree per
  registered repo on branch `f-<feature>` and generates a
  `.code-workspace`. *Success:* one command opens the set; members missing
  locally are named, not guessed.
- **CAP-2 — set-level status + safe teardown.** Dirty/unpushed across the
  set in one command; removal refuses while any member is dirty.
  *Success:* the refusal names the dirty member; --merged-only honors 13.1's
  archive-not-delete discipline per member.

## Constraints
13.1/13.2's single-repo contract is the substrate (deps); the own-worktrees-
only HARD rule extends set-wide (loop homes stay invisible); sibling-org
pattern only, no prose/code import.

## Non-goals
Monorepo migration; bmad-switch scope (kin: bmad-switch-scope-enforcement);
cross-repo atomic commits.

## Success signal
A feature spanning three repos opens, reports, and tears down as one
workspace, with every single-repo guarantee intact per member.

## Spec Change Log

### 2026-08-23 — Registry location (Story 13.3)

- **Decision:** Tracked repo-root **`.steward/repo-sets.yaml`** with a top-level
  `projects:` mapping (the `[projects.<slug>]` shape from the Dream). Example
  shipped as `.steward/repo-sets.example.yaml`.
- **Why:** Matches the established `.steward/` operational-config precedent
  (budget, sync-config, keys-inventory) — survives bmad-switch, is reviewable in
  git, and keeps registry paths operator-declared rather than inferred.
- **Known-bad avoided:** Silently inventing a `pyforge.toml` file this repo does
  not have; guessing clone locations for missing members.

### 2026-09-09 — PARK with a named trigger

- **Decision (operator, batch rows stB-B8 / C7):** park this Spec. **Trigger: "when a second repo
  joins the estate"** — which is **Story 44.3** (python-foundry).
- **Why parking is honest here, not dismissive:** CAP-1 and CAP-2 are built and `done` (Stories
  13.3 / 13.4 — `start_repo_set` / `status_repo_set` / `clean_repo_set` and `.code-workspace`
  generation at `workspace.py:277`, `:394`, `:413`, `:239`; registry path
  `.steward/repo-sets.yaml` at `:38`) and have **never been invoked**. No `.steward/repo-sets.yaml`
  exists — `git ls-files .steward/` returns only `keys-inventory.yaml` plus the two
  `.example.yaml` files. Adopting now would mean writing a repo-set naming a repo that does not
  exist yet.
- **Registry-location question retired** in the same pass: it was answered at 13.3 and is recorded
  in the 2026-08-23 entry above.
