# pyforge-steward

General documentation (architecture, operations, how-tos): docs/MAP.md at the repository root.

Steward — the Provisioner's station: the `steward` CLI (also `pyforge steward …`) for credentials, deployment,
provisioning, budget, sync, workspaces, upgrades, the estate, CI pauses, Pages and the preflight — 31 duties in all.

- **Dream:** `docs/dreams/pyforge-steward.md`
- **Planning:** `_bmad-output/projects/pyforge-steward/planning-artifacts/`
- **Public contract:** `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md`
  lists every verb and flag, the MCP tools and targets, every feature-flag key, environment variable and exit code,
  the entry points, the names other packages import and what steward needs from the tree (spec-pyforge-steward:CAP-179).
  `tests/meta/test_public_contract.py` fails when the code has an item that file lacks.

Story 1.1 delivers the package, the argparse dispatcher, and the `Duty` contract
(canopy:AD-7) with its null engine. `main()` is the sole owner of the process exit code
(canopy:AD-8): a duty returns a `DutyResult` and never calls `sys.exit()` — pinned by
`tests/meta/test_invariants.py`.

Exit codes: `0` ok · `1` a duty ran and failed · `2` usage · `3` a duty's documented refusal (`budget check` with no
metered source, `ci` or `pages` with its flag off, `estate plan` when its pixi dry run fails, `preflight
verify-deferred` that could not run; the full table is in `contract.md`) · `70` internal error · `130` interrupted. A
crash is never reported as `1`, so "the duty failed" and "the tool broke" stay distinguishable.
