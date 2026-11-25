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

**Is this machine ready?** `steward init` answers per kind of work (spec-pyforge-steward:CAP-183):

```bash
pixi run -e pyforge-guild pyforge steward init                      # the desktop profile
pixi run -e pyforge-guild pyforge steward init --profile container  # with the profiles it requires
pixi run -e pyforge-guild pyforge steward init --profile all --json
pixi run -e pyforge-guild pyforge steward init --list               # the profiles and checks; probes nothing
```

The profiles are `desktop` (a clone, the environments, the station CLIs, the tests, the full preflight), `container`
(the platform image and its compose stack), `pod` (the chart on kind), `ocp` (OpenShift Local) and `nkp` (`steward
deploy nic`, linux-64 only). The checks are rows of `docs/governance/machine-readiness.yaml` (schema beside it): a new
requirement is a row, and only a new kind of probe is code (`src/pyforge/steward/machine.py`). Every check that is not
ok prints `remedy (agent|operator): <command>`. The verb installs nothing and writes nothing: a probe inside an
environment runs `pixi run --as-is`, and a deep check (a cluster, one throwaway container) runs only with `--deep`.
It exits 0 when every chosen profile is ready, 1 when one is not (or is unsupported on this platform), 2 for an
unknown profile and 3 when the data file is missing or invalid. The `--json` document (`ok`, `platform`, `profiles[]`,
`checks[]`, and the earlier `prereqs[]`) is described in `contract.md` § *The `init` report*; the walk-through is
`docs/tutorials/onboard-a-machine.md`.

Story 1.1 delivers the package, the argparse dispatcher, and the `Duty` contract
(canopy:AD-7) with its null engine. `main()` is the sole owner of the process exit code
(canopy:AD-8): a duty returns a `DutyResult` and never calls `sys.exit()` — pinned by
`tests/meta/test_invariants.py`.

Exit codes: `0` ok · `1` a duty ran and failed · `2` usage · `3` a duty's documented refusal (`init` with no readable data file, `budget check` with no
metered source, `ci` or `pages` with its flag off, `estate plan` when its pixi dry run fails, `preflight
verify-deferred` that could not run; the full table is in `contract.md`) · `70` internal error · `130` interrupted. A
crash is never reported as `1`, so "the duty failed" and "the tool broke" stay distinguishable.
