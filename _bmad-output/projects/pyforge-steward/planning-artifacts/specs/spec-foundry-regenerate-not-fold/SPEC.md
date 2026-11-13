---
fold-exemption: different-lifecycle
spec: foundry-regenerate-not-fold
status: ready
created: "2026-09-13"
updated: "2026-11-11"
owner-dream: docs/dreams/foundry-regenerate-not-fold.md
extends: spec-python-foundry-cutover
surface: []
companions:
  - ab-sync.md
sources:
  - ../../../../../../docs/dreams/foundry-regenerate-not-fold.md
open_questions: []
---

> **Canonical contract.** Derived from
> `docs/dreams/foundry-regenerate-not-fold.md` and `.memlog.md`. Extends
> `spec-python-foundry-cutover`; cite this file's ids as `fnr:CAP-1..5`.
> Decomposed as steward **Epic 54**. Does not flip any Epic 44 `blocked`
> key. Does not dispatch 44.4, 44.5, or 44.6. Companion `ab-sync.md` is
> the dual-root protocol. CAP-5 starting five-fields on B are the eight
> folded station Specs named in this memlog (marshal and steward 2026-09-16/17;
> atlas, doctor, herald, mason, scribe, warden 2026-09-17).

# SPEC — Foundry regenerate, not fold

## Why

**A mandate to meet and a vision to realize.** Launch the Foundry / Adopt
Frames / Build the Intelligence Hub / Wire the BMAD-suite cannot be a
`src/shared/packages` path-rename. Foundry is a clean BMAD-on-B tree.
local-recipes is the A control and legacy oracle. The shared starting
contract is the Dream plus its memlog (`archive/**/.memlog.md` included,
no backfill), from which the Spec five-fields are re-derived; a Frame is
a pointer to them, not a seed. Behavior is A/B tested. Historical PRD /
arch / epics / comments stay on A.

## Capabilities

- **CAP-1 — Thin oracle.** (shipped 2026-11-10, Stories 54.1 and 120.5)
  - **intent:** The operator can freeze a small archived suite that is
    also the A/B case list for the foundry kernel and the oracle of the
    Launch slice.
  - **success:** A tracked list of existing core / steward / marshal
    cases lives with this Spec (`case-list.md`; on B after 54.5); every
    `spec-python-foundry-cutover` `launch-slice.md` step that has an A
    test has a row;
    `src/shared/packages/pyforge-steward/tests/meta/test_cutover_case_list.py`
    holds the count line equal to the rows and exits 0; those cases run
    against foundry trees; Frame frontmatter preflight alone is not
    acceptance.

- **CAP-2 — Rebuild `pyforge-core` in foundry.** (ready 2026-11-10; not met: green on B against today's core contract, as B holds a prototype at the PR #1344 pin that passed its slice 2026-09-14 and is not re-pinned until the truth sweep, DW-steward-121-2)
  - **intent:** Foundry gains `station_port`, hooks, and the cutover-root
    reader as a new leaf under `src/packages/`, rebuilt from Dream plus
    memlog and the re-derived Spec (a Frame points at them), not a copy of
    `src/shared/packages/pyforge-core`.
  - **success:** The public core contract plus the CAP-1 core slice are
    green on B, with an A/B row that is not `diverge`.

- **CAP-3 — Rebuild steward in foundry.** (ready 2026-11-10; not met: green on B against today's steward contract, as B holds a prototype at the PR #1344 pin that passed its slice 2026-09-14 and is not re-pinned until the truth sweep, DW-steward-121-2)
  - **intent:** `pyforge steward` (provision, workspace, guards, cutover,
    suite register path) exists as an engine regenerated from Dream plus
    memlog and the re-derived Spec, with CLI and MCP; the Frame check is
    the `frame-preflight` task, not a duty.
  - **success:** Steward's CAP-1 slice is green on B with an A/B row;
    implementation commits land only in a python-foundry worktree.

- **CAP-4 — Rebuild marshal in foundry.** (ready 2026-11-10; not met: green on B against today's marshal contract, as B holds a prototype at the PR #1344 pin that passed its slice 2026-09-14 and is not re-pinned until the truth sweep, DW-steward-121-2)
  - **intent:** `pyforge marshal` cursor-native dispatch exists as an
    engine regenerated from Dream plus memlog and the re-derived Spec,
    with CLI and MCP.
  - **success:** One dispatch against the foundry remote plus the CAP-1
    marshal slice are green with an A/B row. Drain corners not in the
    thin list stay on A until `fnd:CAP-9` / 44.14 grows the list.

- **CAP-5 — Dual-root A/B.** (shipped 2026-11-10, Stories 54.5 and 120.2)
  - **intent:** The operator can keep one starting contract across two
    git roots and compare behavior without copying BMAD trees or code.
  - **success:** `ab-sync.md` is in `companions:`; A writes every Dream,
    Frame, Spec and the capability ledger until the flip, and B reads A at
    the SHA in its `docs/foundry/PIN.md` and writes none of them; the flip
    hands the writer lock to B (`fnd:CAP-8`); B (after 54.5) has a pin
    file and a case-list stub; `diverge` blocks `verified-in-foundry`; no
    `_bmad-output` rsync.
    B's starting station five-fields are `spec-pyforge-marshal`,
    `spec-pyforge-steward`, `spec-pyforge-atlas`, `spec-pyforge-doctor`,
    `spec-pyforge-herald`, `spec-pyforge-mason`, `spec-pyforge-scribe`,
    and `spec-pyforge-warden` (one-chain CAP-7). Do not fold those
    Specs again on B — regenerate.

## Constraints

- A writes every Dream, Frame, Spec and the capability ledger until the
  `pyforge.cutover_root` flip; B reads A at the SHA in its
  `docs/foundry/PIN.md` and writes none of them; the flip hands the
  writer lock to B.
- Factory / CFE / recipes stay invented on A until a foundry CFE exists.
  Kernel package commits only on B.
- The eight folded station Specs on A are B's starting contracts
  (`spec-pyforge-atlas`, `spec-pyforge-doctor`, `spec-pyforge-herald`,
  `spec-pyforge-mason`, `spec-pyforge-scribe`, `spec-pyforge-warden`,
  plus marshal and steward). B also inherits Dream-append-first, the
  fold-exemption list, the seam rule, FR ← CAP, and companions-as-record.
  Regenerate on B; do not fold again.
- Public CLI verbs stay (`pyforge steward`, `pyforge marshal`, `warden scan`).
- `steward cutover apply --phase 1a` is not how packages appear.
- `pyforge.cutover_root` stays `local-recipes` until the operator flips it by hand, with no loop running, once the Launch slice is
  proven: B lands one story on itself through its own dispatch and its own detectors,
  and every Launch row of the case list reads `verified-in-foundry`. Nothing flips it
  automatically, and a flip is refused while a loop runs.
- Never commit on the shared local-recipes checkout; never
  `scripts/bmad-switch` from a parallel agent.
- Do not flip Epic 44 `blocked` keys (44.1, 44.2, 44.4, 44.5, 44.6, 44.8, 44.9,
  44.10, 44.11, 44.14, 44.15); 44.1 and 44.4 to 44.6 retired 2026-11-10 and
  44.10 on 2026-09-25.

## Non-goals

- Folding `src/shared/packages/` via 44.4 / apply phase 1a.
- Host, `/console/`, or seven `django-*` portals in Launch.
- Renaming public CLI verbs.
- conda-forge / staged-recipes / feedstock PRs (44.9).
- Copying the recipe universe (44.8) or archiving local-recipes (44.10).
- Waiting for a complete 44.14 oracle before the kernel exists.
- Moving the CFE cell (44.6). Foundry CFE is rebuilt from Specs; A is the oracle.
- Byte-sync of PRD, ARCH, epics, sprint files, stories, or package trees.

## Success signal

A new builder can open B, read the slim kit, and implement in
`src/packages/` without reading A's cutover novel. Kernel CLI + MCP on B
pass the shared case list; A/B rows are not `diverge`; no package fold
and no host.

## Assumptions

- Factory island (44.7) and the cutover flag (44.12) already exist on
  foundry / local-recipes and stay.
- Frames (53.2) and Hub objects (53.1–53.4) on A are the first pin
  targets, not cargo to fold.
