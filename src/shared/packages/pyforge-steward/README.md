# pyforge-steward

Steward — the Provisioner's station. `steward keys / deploy / provision / budget`.

- **Dream:** `docs/dreams/pyforge-steward.md`
- **Planning:** `_bmad-output/projects/pyforge-steward/planning-artifacts/`

Story 1.1 delivers the package, the argparse dispatcher, and the `Duty` contract
(AD-7) with its null engine. `main()` is the sole owner of the process exit code
(AD-8): a duty returns a `DutyResult` and never calls `sys.exit()` — pinned by
`tests/meta/test_invariants.py`.

Exit codes: `0` ok · `1` a duty ran and failed · `2` usage · `70` internal error
· `130` interrupted. A crash is never reported as `1`, so "the duty failed" and
"the tool broke" stay distinguishable.
