---
title: "76.1: The one flag tree carries per-environment values, so off in production is a value"
type: 'feature'
created: '2026-09-28'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: flag-infrastructure
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
  - src/platform/config/flags.json
  - src/shared/packages/django-pyforge/src/django_pyforge/flags.py
  - src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py
  - src/platform/deploy/charts/platform/templates/flags-configmap.yaml
  - src/platform/tests/test_openfeature_file_flags.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the Guild's rule (`spec-feature-flag-governance`, ready 2026-09-28) needs every new capability's flag to be
"off in production, on in staging and dev", and its gate (CAP-2, doctor's) needs to read that per-environment default. The
one tree, `src/platform/config/flags.json` (canopy:AD-11, Story 26.4), has one `defaultVariant` per flag and no notion of
an environment: the chart mounts it as one ConfigMap (`--set-file flags.tree=…`) and every environment gets the same
values. The spine's Deferred row *FILE flag env promotion overlays* left the values to ops. The CLI side reads the same
tree through `pyforge.core.flags.read_boolean`, which Story 75.1 adds in `cutover_root`'s shape; it knows no environment
either.

**Approach** (canopy:AD-11 amended 2026-09-28; this story takes up the Deferred row):

- `src/platform/config/flag-overlays.json` (new) is one value-only document keyed `dev`, `staging`, `production`; each maps
  a key the tree defines to one of that flag's variant names. The tree stays the only definition of every flag.
- `pyforge.core.flags` (Story 75.1's module, in `pyforge-core` as `pyforge.core.cutover_root` is) gains:
  - the environment, from `PYFORGE_ENVIRONMENT` (`dev` when unset, for local development; anything outside the three is a
    named error);
  - composition: the tree with each overlaid `defaultVariant` replaced, a flag whose tree `state` is `DISABLED` left off in
    every environment (doctor's kill switch wins);
  - validation, each a named error: an overlay key the tree lacks, a variant the flag lacks, an unknown environment, an
    overlay entry that is not a variant name (a definition is a second tree);
  - `render(environment) -> bytes`; `read_boolean` reads the rendered tree for the current environment.
- `django_pyforge.flags` configures the host's FILE provider from the same rendered tree (`resolve_flags_path` and
  `evaluate_from_source` go through `pyforge.core.flags`), and gains a `render --environment <env>` verb that writes the
  rendered tree for the chart.
- The chart: `flags.environment` is required and one of the three; the ConfigMap carries the rendered tree for that
  environment; `PYFORGE_ENVIRONMENT` is set on every workload that reads flags. A `flags-render` pixi task feeds
  `--set-file flags.tree=` only if the chart cannot compose the two files itself.
- The overlay document starts with every existing key at its current value in all three environments, so no evaluated
  value changes on landing.
- Routing the CLI reader through OpenFeature, with the packages that needs, is Story 76.3's.

Ledger key: `76-1-the-one-flag-tree-carries-per-environment-values-so-off-in-production-is-a-value`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-75.1 (the reader this story extends).

### Living CAP citations

- `spec-feature-flag-governance` CAP-5 (steward's, per its *Who does the work* table); its constraint "off in production
  waits for CAP-5".
- canopy:AD-11 (amended 2026-09-28: value-only overlays, one rendered tree per environment); the spine's Deferred row
  *FILE flag env promotion overlays*.
- Kinship: Story 75.1 adds the reader this story extends; Story 76.3 routes it through OpenFeature; doctor's CAP-2 gate
  reads the rendered per-environment values.

## Acceptance Criteria

- Given the overlay document names `off` for a key in `production` only When the tree is rendered for each environment Then `production` carries `off`, `staging` and `dev` keep the tree's variant, and the host provider, `evaluate_from_source` and `pyforge.core.flags.read_boolean` agree for every key in every environment
- Given a flag whose tree `state` is `DISABLED` When it is rendered for any environment Then it evaluates off, whatever the overlay says
- Given an overlay key the tree lacks, a variant the flag lacks, an environment outside `dev` / `staging` / `production`, or an overlay entry that is an object When the tree is composed Then a named error names the offending entry
- Given `PYFORGE_ENVIRONMENT` unset When `read_boolean` reads Then it reads the `dev` rendering; set to `qa` Then it refuses with a named error and never reads as ON
- Given the chart rendered without `flags.environment` When `helm template` runs Then it fails naming the value; rendered for `production` and `dev` Then the two ConfigMaps differ exactly by the overlay values
- Given the landing When every existing key is evaluated in every environment Then no value differs from before
- Given the change When `pixi run --frozen -e pyforge-steward pyforge-steward-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- One tree, one provider, no egress; the overlay holds values only.
- Keep `src/platform/` free of `pyforge.*` imports: the chart and the host read files; `django_pyforge` may import
  `pyforge.core`, as it already does for `cutover_root`.
- Reconcile every Spec `spec-surface-check` names (`spec-pyforge-core` for `pyforge-core`, `spec-pyforge-steward` and
  `spec-pyforge-unifying-strategy` for `django-pyforge` and `src/platform`), then stamp each scoped.
- Keep `read_boolean`'s fleet-wide contract (Story 75.1: signature, resolution order, OFF/absent semantics, the Q3
  helpers) unchanged; the environment is an additive input, never a new required argument.
- If a `flags-render` task is added, `pixi.toml` changes: regenerate `environment.yaml` and run
  `pixi run -e pyforge-guild pyforge-station-tests` before pushing.

**Never:**
- No flagd daemon, no sidecar, no hosted service, no environment variable as a provider, no targeting rule (Q5).
- Do not add OpenFeature to a station CLI environment here (Story 76.3 does).
- Do not edit the Guild Spec or its memlog.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| overlaid key | `production: {k: off}` | production renders `off`; others keep the tree's | — |
| kill switch | tree `state: DISABLED` | off everywhere | — |
| unknown key | overlay names a key the tree lacks | — | named error |
| unknown variant | overlay names `maybe` | — | named error |
| definition in overlay | overlay entry is an object | — | named error (a second tree) |
| unknown environment | `PYFORGE_ENVIRONMENT=qa` | — | named error, never ON |
| chart, no environment | `helm template` without `flags.environment` | — | render fails naming it |

</intent-contract>

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-5 (the Guild's; ready 2026-09-28), the
steward spine's canopy:AD-11 amendment and Deferred row of 2026-09-28, and the `spec-pyforge-steward` memlog notes of
2026-09-28 (night) recording Epic 76's shape and the CLI reader.

## Binding

Parent Spec capability: `spec-feature-flag-governance` CAP-5 (the Guild's Spec; no station CAP or FR is minted, as doctor
Epic 24 does for `spec-coverage-gate-independence`).
Dream: `docs/dreams/feature-flag-governance.md`.
Ledger key: `76-1-the-one-flag-tree-carries-per-environment-values-so-off-in-production-is-a-value`.
Ledger status at mint: `backlog`.
Deps: S-75.1 (the `pyforge.core.flags` reader this story extends).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run --frozen -e pyforge-guild pytest src/shared/packages/pyforge-core/tests/unit/test_flags.py -q` — expected: pass
  (composition, validation, the environment, and `read_boolean` over the rendered tree).
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: `test_openfeature_file_flags.py` (the host provider
  and `read_boolean` agree per environment) and `test_chart_invariants.py` pass with `helm` on `PATH`.
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings.

## Review Triage Log
