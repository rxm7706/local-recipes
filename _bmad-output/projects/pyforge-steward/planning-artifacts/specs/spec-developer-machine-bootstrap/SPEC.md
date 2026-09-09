---
spec: developer-machine-bootstrap
status: in-progress   # 2026-09-09 (batch Class B row stA), was `ready`: Epic 17 is 2/2 `done` and
                      # the four verbs are live (`pyforge/steward/cli.py:51-54,:89-101,:166`), but
                      # this Spec's own success signal — a recorded clean-container run, nothing ->
                      # validate-fast, zero improvised steps — has never run, and `spec-17-2` is a
                      # 54-line contract husk with no dev log.
updated: "2026-09-09"
owner-dream: docs/dreams/developer-machine-bootstrap.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/developer-machine-bootstrap.md
open_questions:
  # ANSWERED 2026-09-09 (batch rows stA-B4 / C17): "podman-in-podman or a dedicated CI lane?" —
  # NEITHER in local-recipes. Run the proof as a DEDICATED CI LANE against `python-foundry`, after
  # Story 44.3. Story 44.10 archives local-recipes, so proving a bootstrap against the repo that is
  # about to stop being the working tree buys nothing; a dedicated lane also avoids the
  # privileged-nesting surface podman-in-podman would add for one job. This places the Dream
  # `foundry-side`. The residue that remains genuinely open:
  - "The proof itself has never run. It is now foundry-side: the dedicated `python-foundry` CI lane
    is gated on Story 44.3, so this Spec cannot reach its own success signal inside local-recipes.
    Who schedules that lane, and against which foundry milestone, is undecided."
---

# SPEC — A fresh machine reaches validate-fast through steward verbs

## Why
Onboarding is undocumented ritual: pixi + git + gh + podman + clones + env
installs + hooks, hand-driven per machine. The sibling PyForge org's
same-name dream contributes a proven command surface (pattern only —
unlicensed; intake report 2026-08-22).

## Capabilities
- **CAP-1 — bootstrap verbs.** *Intent:* `steward init` (prereq detection
  with floors from the pixi version registry), `shell-init`, `setup`
  (clone + pixi install + hooks), `initrepo` — fresh machine to
  validate-fast green. *Success:* the flow reproduces in a clean container;
  every prereq failure names its remedy.

## Constraints
Consumes provision --env/--runner (Epic 3), the OCP 12.4 bring-up, and the
fifteen-factors devinfra substrate — never duplicates them; floors read
`scripts/pixi_version_registry.py`.

## Non-goals
Cluster bring-up (12.4); backing services (fifteen-factors); multi-repo
workspaces (Epic 13 extension).

## Success signal
A recorded clean-container run: nothing → validate-fast passing, zero
improvised steps.

*(Unmet as of 2026-09-09. The verbs are live and Epic 17 is `done`, but no such run has ever been
recorded — which is why the Spec sits `in-progress`, not `shipped`. The run's home is a dedicated
CI lane against `python-foundry` after Story 44.3, not podman-in-podman here.)*
