# pyforge-core

The shared leaf every pyforge station may depend on, and that depends on
none of them. Pure stdlib, zero third-party runtime dependencies — the
floor Stories 14.2-14.4 will extract the atomic-write primitive, verdict
lattice, report envelope, exception root, and subprocess guard into. See
[`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md`](../../../../_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md)
for the full contract.

**Status:** Story 14.1 scaffolds the empty package and its leaf-constraint
meta-test only — no primitive has been extracted into it yet.

## Develop

Run from the repository root (the parent pixi workspace):

```bash
pixi run -e pyforge-core pyforge-core-test  # run the test suite
```

The `pyforge-core` environment is lean by design (`no-default-feature`): it
carries only the built package (stdlib only, no runtime dependency beyond
`python`) and a test runner.

## The leaf constraint

`tests/meta/test_leaf_constraint.py` structurally enforces two rules for
every module under `pyforge.core`:

- no import from `pyforge.<X>` for any `X != "core"` — no station import,
  ever;
- no import outside `sys.stdlib_module_names` and the `pyforge` namespace
  itself — no third-party runtime dependency, ever.

Both guards are proven non-vacuous against synthetic-violation fixtures,
not just by scanning the (currently near-empty) real package.
