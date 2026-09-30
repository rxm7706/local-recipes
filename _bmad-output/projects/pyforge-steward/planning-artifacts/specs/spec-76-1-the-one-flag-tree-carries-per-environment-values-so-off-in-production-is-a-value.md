---
title: "76.1: The one flag tree carries per-environment values, so off in production is a value"
type: 'feature'
created: '2026-09-28'
status: 'done'
baseline_revision: '6b7d586b33fdf7edf7b54b81c9cacc8f33efffa7'
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
warnings: [oversized]
deferred:
  - summary: >-
      The new helm-gated chart tests may skip silently in the Platform CI `test` job.
    evidence: |-
      Every chart test carries `requires_helm` (skip when `helm` is not on PATH). The `test` job
      runs on `ubuntu-latest` in the slim `platform-ci-test` pixi env, which has no
      `kubernetes-helm` (only `platform-dev` does). Whether the runner supplies its own `helm` was
      not verified here. Settled by reading the job log of a Platform CI `test` run for a skip
      count on `tests/test_chart_invariants.py` and `tests/test_openfeature_file_flags.py`. The
      same pattern covers every pre-existing chart test.
    location: >-
      .github/workflows/platform-ci.yml
    severity: medium (unverified)
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

## Code Map

- `src/shared/packages/pyforge-core/src/pyforge/core/flags.py` -- Story 75.1's reader (`read_boolean`, `require`, `disabled_help`, `FlagOff`); gains environment, `compose`, `render`, the named errors. Tree path reuses `cutover_root.resolve_flags_path` (unchanged).
- `src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py` -- read-only: path resolver reuse; its string reader is not overlay-aware (out of scope; boolean flags only).
- `src/shared/packages/django-pyforge/src/django_pyforge/flags.py` -- host FILE provider glue: `resolve_flags_path`, `read_flag_tree_bytes`, `evaluate_from_source`, `evaluate_cutover_root`, `main`; callers `apps.py` (`configure_from_env`), `config/urls.py` (`tree_view`, `eval_view`), doctor `__main__.py` (`resolve_flags_path`).
- `src/platform/config/flags.json` -- the one tree, unchanged; `src/platform/config/flag-overlays.json` (new) -- the value-only overlay document.
- `src/platform/deploy/charts/platform/{values.yaml,templates/flags-configmap.yaml,templates/_helpers.tpl,templates/NOTES.txt}` -- ConfigMap composes tree + overlays for `flags.environment`; `PYFORGE_ENVIRONMENT` joins `PYFORGE_FLAGS_PATH` in the shared env define (every flag-reading workload).
- `src/platform/tests/{test_openfeature_file_flags.py,test_chart_invariants.py}` -- host provider vs `read_boolean` agreement; chart render, `_helm` default args.
- `scripts/flag_gate_check.py` -- `orphan_keys` treats any tracked `src/` file naming a key as its reader; the overlay names every key, so it joins the tree as a non-reader.
- Chart callers to keep working: `.github/workflows/platform-deploy.yml`, overlay READMEs, `docs/explanation/platform-deployment-architecture.md`.

## Tasks & Acceptance

**Execution:**
- `src/platform/config/flag-overlays.json` -- new; `dev` / `staging` / `production`, each key at its current `defaultVariant` -- no evaluated value changes on landing
- `src/shared/packages/pyforge-core/src/pyforge/core/flags.py` -- `PYFORGE_ENVIRONMENT` (`dev` when unset, else one of three), `compose` (validate every overlay entry, replace `defaultVariant` for the environment, skip a `DISABLED` flag), `render` -> bytes, sibling `flag-overlays.json` discovery, `read_boolean` reads the composed tree; named errors -- one implementation for CLI and host
- `src/shared/packages/pyforge-core/tests/unit/test_flags.py` -- I/O matrix rows, environment handling, `read_boolean` per environment, unchanged 75.1 semantics
- `src/shared/packages/django-pyforge/src/django_pyforge/flags.py` -- `resolve_flags_path` returns a path whose content is the rendered tree (materialised via core when an overlay sits beside the tree), `read_flag_tree_bytes` rendered, `render --environment <env>` verb -- host provider and CLI read the same bytes
- `src/platform/deploy/charts/platform/` -- `flags.environment` required and validated, `flags.overlays` file, ConfigMap composed, `PYFORGE_ENVIRONMENT` env -- chart can compose, so no `flags-render` task and no `pixi.toml` change
- `src/platform/tests/` + chart callers (`.github/workflows/platform-deploy.yml`, overlay READMEs, docs, `NOTES.txt`) -- pass `flags.overlays` and `flags.environment`; agreement and chart tests
- `scripts/flag_gate_check.py` -- overlay is not a reader -- keeps orphan detection honest
- Governed paths -- name each on the owning Spec memlog and every co-governor `spec-surface` names (append only; no `--write-baseline`)

**Acceptance Criteria:**
- Given the intent-contract ACs, when the core, host and chart tests run, then each AC has a test that observes it at its outermost surface (`read_boolean`, provider value, `helm template`)

## Spec Change Log


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

## Design Notes

- Overlay discovery: `flag-overlays.json` beside the resolved tree. The in-cluster mount holds the already rendered tree with no sibling, so it reads as is; the repo checkout composes on the fly. `PYFORGE_ENVIRONMENT` is validated on every read either way.
- An invalid environment or overlay raises a named `ValueError` subclass from `read_boolean`. A WARN plus `default` could read ON for a retrofit `default=True`, which the AC forbids.
- The chart composes with `fromJson` / `set` / `toPrettyJson` and repeats the validation with `fail`; a test asserts the ConfigMap equals `pyforge.core.flags.render(env)` parsed, so the two cannot drift silently.

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

### 2026-09-29 — Review pass
- verdicts: 43 findings — high 6, medium 6, low 21, false 8, maybe-false 2
- findings:
  - `[high]` `[patch]` (Blind Hunter) `pyforge.cutover_root` has two answers: the overlay pins it, the composed readers honour that, `read_cutover_root` reads the raw tree — verified by running a flip to `foundry` under PYFORGE_ENVIRONMENT=production (raw `foundry`, rendered `local-recipes`). Patched: `read_cutover_root` composes the sibling overlay for the current environment (lazy import, `FlagConfigError` re-raised as `CutoverRootError`); `flip_root` sets the target in every overlay environment that names the key, validating the overlay before writing either file; tests in pyforge-core `test_cutover_root.py`, steward `test_cutover.py` and the platform shipped-pair test (now including the string key).
  - `[low]` `[reject]` (Blind Hunter) The overlay repeats every tree value and nothing keeps the two in step — the intent itself mandates "every existing key at its current value in all three environments"; the one concrete harm named (a masked cutover flip) is patched in the row above; a tree/overlay drift check is a new capability the intent does not ask for.
  - `[medium]` `[patch]` (Blind Hunter) A bad PYFORGE_ENVIRONMENT crashes every steward command with exit 70 — reproduced with `qa` (traceback, exit 70) because `build_parser` calls `disabled_help` -> `read_boolean`. Patched: `main()` catches `FlagConfigError` beside `FlagOff` and returns `EXIT_USAGE` with the named message; tests for `--help`, `keys`, and a bad overlay. The blank-value sub-claim is not a defect: the intent says anything outside the three is a named error.
  - `[low]` `[reject]` (Blind Hunter) Local-dev flips no longer reach a running FILE provider — in a checkout the rendered copy is written when `resolve_flags_path` runs, so later edits need another call. Real, but checkout-only (the in-cluster mount has no sibling overlay and is polled live), fixed by restarting, and the fix is a refresh mechanism, not a direct correction. Documented in the `resolve_flags_path` docstring instead.
  - `[medium]` `[patch]` (Blind Hunter) The doctor `resolve_tree_path` change has no test — confirmed: reverting the import leaves every test green. Patched: a doctor test drives `flags kill-switch` with no `--flags-path` against a tree with a sibling overlay and asserts the tree file itself is `DISABLED` (fails when the import is reverted).
  - `[high]` `[patch]` (Blind Hunter) `AppConfig.ready()` needs an undeclared dependency — first cleared against the main image (which copies `pyforge/core`), then found real for the mcp-host sidecar: its settings list `django_pyforge` in INSTALLED_APPS, its Containerfile copies no `pyforge/core`, and `resolve_flags_path()` raised `ModuleNotFoundError: No module named 'pyforge'` where the baseline returned None. Patched: both resolver paths catch `ImportError` and fall back to the tree as it is; a platform test blocks `pyforge`, `pyforge.core` and `pyforge.core.flags` in `sys.modules`.
  - `[low]` `[patch]` (Blind Hunter) The docs claim "renders the same bytes" — Helm's `toPrettyJson` sorts keys and escapes HTML characters while Python keeps insertion order; only the parsed content is equal. Patched: the architecture doc says "the same content once parsed" and names the difference.
  - `[low]` `[reject]` (Blind Hunter) The chart re-implements composition in Go templates with no shared vectors — the intent permits the chart composing ("a flags-render task only if the chart cannot"); parity is tested at parsed-JSON equality and on the four refusal classes.
  - `[low]` `[patch]` (Blind Hunter) The PYFORGE_ENVIRONMENT chart test is tautological and the doc says "every platform pod" — the test only looked at containers already carrying PYFORGE_FLAGS_PATH. Patched: it now asserts the variable, equal to the release environment, on every container (init containers and CronJob pods included) that mounts the `flags` volume; the doc says "every workload that reads flags".
  - `[low]` `[reject]` (Blind Hunter) "No value differs on landing" is only checked for dev in the chart — a permanent staging/production equality test would fail exactly when an overlay legitimately turns a flag off, which is this story's purpose; the property was verified at landing (9 key/environment pairs, 0 differences).
  - `[low]` `[reject]` (Blind Hunter) The host-fetch path never validates the client's environment — the fetched bytes are the host's own rendering, so the client's variable is irrelevant by design; no harm shown.
  - `[false]` `[reject]` (Blind Hunter) Spec-surface hygiene incomplete — `python scripts/spec_surface_reconcile.py` and `pixi run -e pyforge-guild spec-surface-check` both exit 0 with the baseline file at the baseline revision; this run forbids `--write-baseline`, so no stamp is expected, and the memlogs name the governed paths.
  - `[low]` `[patch]` (Blind Hunter) `render --output` uses a bare write and lets `OSError` escape — patched: `render_main` catches `OSError`, prints `cannot write <path>: …` and returns 1; test covers a file parent and a directory path.
  - `[low]` `[reject]` (Blind Hunter) A positional flag key literally named `render` reads as the verb — no such key exists (keys are dotted, `pyforge.<name>`).
  - `[low]` `[reject]` (Blind Hunter) `<dev|staging|production>` placeholders paste as a shell pipe — the surrounding docs already use `<digest>`-style placeholders; a pasted literal fails either way.
  - `[low]` `[reject]` (Blind Hunter) `_FLAGS_RENDER_ARGS` duplicates the argv building of `_helm_core` in the other test module — test-only duplication, no behaviour at stake.
  - `[false]` `[reject]` (Blind Hunter) The `"--set-file" not in args` guard in `_helm` drops the defaults when a test passes an unrelated `--set-file` — the chart then fails loudly on the required `flags.environment`, so nothing renders wrongly.
  - `[low]` `[reject]` (Blind Hunter) The core test reaches `src/platform/config` through `parents[6]` and skips when the tree is absent — that test is the check that the shipped pair composes; skipping outside a checkout is the intended degrade.
  - `[high]` `[patch]` (Edge Case Hunter) `flip_root` edits only the tree while the overlay pins the key, so a flip reports `foundry` while the chart and host serve `local-recipes` — same defect and fix as the first row.
  - `[low]` `[reject]` (Edge Case Hunter) `_materialise` writes the checkout rendering once and it goes stale — same root cause and disposition as the local-dev row above.
  - `[low]` `[reject]` (Edge Case Hunter) `configure_file_provider`'s `setdefault(PYFORGE_FLAGS_PATH, …)` points later resolves at the frozen copy — verified, but it is the same checkout-only snapshot behaviour; a corrective would change what the setdefault means for every caller.
  - `[medium]` `[patch]` (Edge Case Hunter) Steward `main()` maps only `FlagOff` — same defect and fix as the steward exit-70 row.
  - `[false]` `[reject]` (Edge Case Hunter) An unset PYFORGE_ENVIRONMENT silently reads `dev` on a production-side CLI — the intent specifies "`dev` when unset, for local development".
  - `[false]` `[reject]` (Edge Case Hunter) `tree_view` turns a bad environment into an opaque 500 — the process already failed loudly at `AppConfig.ready()`; a loud failure on a bad configuration is the required behaviour.
  - `[low]` `[patch]` (Edge Case Hunter) `render_main --output` can raise `OSError` — same fix as the render row above.
  - `[maybe-false]` `[reject]` (Edge Case Hunter) The `atexit` rmtree could delete a shared render directory when a forked worker exits — reachable only in a checkout with an overlay beside the tree (the in-cluster path never materialises) and an unshown pre-fork call; if true it is low, and the guard is extra complexity. Would settle it: a preload-forked run of `configure_from_env` in a checkout.
  - `[false]` `[reject]` (Edge Case Hunter) `_helm` appends `flags.environment=dev` after a caller's own value — no caller passes one through `_helm`; the new tests build their own argv.
  - `[low]` `[patch]` (Edge Case Hunter) "Same bytes" claim — same fix as the docs row above.
  - `[low]` `[patch]` (Edge Case Hunter) The OCP bring-up doc's two core-chart `helm install` commands omit the flag inputs the chart requires — patched: both pass `flags.tree`, `flags.overlays` and `flags.environment=dev`, with a note that the value is required.
  - `[high]` `[patch]` (Edge Case Hunter) "One implementation for CLI and host" is false for `read_cutover_root` — same defect and fix as the first row.
  - `[low]` `[patch]` (Edge Case Hunter) "PYFORGE_ENVIRONMENT is set on every platform pod" — same doc fix as the env-test row above.
  - `[medium]` `[patch]` (Verification Gap) The kill switch's move to the unrendered tree has no test — same defect and fix as the doctor row above.
  - `[high]` `[patch]` (Verification Gap) `cutover_root` readers ignore the overlay that now pins the flag — same defect and fix as the first row.
  - `[medium]` `[patch]` (Verification Gap, other findings) A bad PYFORGE_ENVIRONMENT makes every steward invocation exit 70 — same defect and fix as the steward row above.
  - `[false]` `[reject]` (Verification Gap, other findings) `ready()` raises outward on a bad environment and no test exercises it — fail-closed is the intended behaviour, and the missing-`pyforge.core` case that could abort `ready()` is patched in the mcp-host row.
  - `[maybe-false]` `[defer]` (Verification Gap, other findings) The new helm-gated chart tests may skip in the Platform CI `test` job because `platform-ci-test` has no `kubernetes-helm` — could not tell whether the runner supplies a `helm`; if true, medium (unverified) and shared with every existing chart test. Recorded in frontmatter `deferred`.
  - `[high]` `[patch]` (Intent Alignment) A third reader (`read_cutover_root`, steward's flip) ignores the overlay — same defect and fix as the first row.
  - `[low]` `[reject]` (Intent Alignment) Two independent composition implementations (Python and Helm) — same disposition as the Go-template row above.
  - `[low]` `[reject]` (Intent Alignment) The checkout provider reads a snapshot — same disposition as the local-dev row above.
  - `[false]` `[reject]` (Intent Alignment) The production-versus-dev ConfigMap criterion is proven on fixtures only — the shipped overlay is identical across environments by the intent's own instruction, so a fixture is the only way to show ConfigMaps differing by overlay values; not a defect.
  - `[low]` `[reject]` (Intent Alignment) "No value differs on landing" is pinned indirectly — same disposition as the dev-only row above.
  - `[false]` `[reject]` (Intent Alignment) Extra strictness beyond the listed refusals (chart requires `flags.overlays`; every environment validated whichever is rendered) — required to compose at all, and the intent asks for validation; not a defect.
  - `[medium]` `[patch]` (Intent Alignment) `resolve_flags_path` changed meaning, reaching doctor's actuator and the gate's reader list — the doctor half is the doctor row above; the gate's exclusion of the overlay is covered by `tests/scripts/test_flag_gate_check.py`.

### 2026-09-29 — Review pass (follow-up)
- verdicts: 32 findings — high 1, medium 4, low 15, false 9, maybe-false 3
- findings:
  - `[low]` `[reject]` (Blind Hunter) carried: the temp render leaks into `PYFORGE_FLAGS_PATH` (`configure_file_provider`'s `setdefault`), so later resolves in that process return the frozen copy — same location and claim as the first pass's `setdefault` row; the `resolve_flags_path` docstring that row leaned on overstated the refresh, corrected under the Verification Gap row below.
  - `[medium]` `[patch]` (Blind Hunter) `flip_root` validates the overlay only as parseable JSON and writes two files non-atomically — confirmed in `cutover.py`: `load_overlays` checks only that the document is an object, so `"pyforge.typo": "off"` flips both files and then `read_cutover_root` raises; the code comment and memlog said "validated". Patched: `flip_root` composes the overlay it will write (`pyforge.core.flags.compose`, every entry of every environment) before either write and refuses with `flip refused: <named entry>`; four new `test_cutover.py` cases (unknown key, unknown variant, unknown environment, object entry) assert the named entry and both files unchanged, and fail with the compose line removed (4 failed, 11 passed). The second-write `OSError` half is rejected low: a failed atomic write on a tracked file is not a state this diff makes likely, and a rollback is added machinery.
  - `[maybe-false]` `[defer]` (Blind Hunter) carried: the helm-gated chart tests may skip in the Platform CI `test` job — same claim as the existing frontmatter `deferred` entry (`.github/workflows/platform-ci.yml`); not added a second time.
  - `[low]` `[reject]` (Blind Hunter) carried: the chart re-implements composition in Go templates, with parity tested on four refusal classes — same row as the first pass; the additional branches named here match Python (`upper (toString state)` equals `.upper()`, a `null` or `[]` environment value is refused by both).
  - `[low]` `[reject]` (Blind Hunter) Only `test_flags.py` clears `PYFORGE_ENVIRONMENT`, so an exported ambient value fails unrelated tests — no pixi task, workflow or conftest sets it, a failure is a named error, and the fix is an autouse fixture in each of three packages (more than a direct correction).
  - `[false]` `[reject]` (Blind Hunter) The `read_boolean` docstring says "never an exception" and then raises — the parenthetical is scoped to the listed absent/unreadable cases, and the next paragraph states the `FlagConfigError` raise; the steward blast radius is the first pass's exit-70 row, already patched.
  - `[low]` `[reject]` (Blind Hunter) carried: the shipped overlay repeats every key and only `dev` is compared with the tree — same as the first pass's dev-only rows.
  - `[low]` `[reject]` (Blind Hunter) The CD render never asserts the production ConfigMap values — the shipped overlay holds every key at the tree's value in every environment, so there is no `off` in production to assert yet; a value assertion is a new check the intent does not ask for.
  - `[false]` `[reject]` (Blind Hunter) The required `flags.environment` / `flags.overlays` break existing releases with no upgrade note — the intent makes `flags.environment` required, the failure names the value, and every in-repo caller (workflows, overlay READMEs, OCP bring-up) passes both.
  - `[low]` `[reject]` (Blind Hunter) `render` verb gaps (unguarded `pyforge.core` import, non-atomic `--output`, no in-repo chart consumer, `render` as first positional) — the verb is a developer tool the mcp-host image never runs, nothing reads `--output` while it is written, the intent still asks for the verb, and the positional case is the first pass's rejected row.
  - `[low]` `[reject]` (Blind Hunter) carried: the checkout render directory goes stale and its `atexit` cleanup could fire in a forked worker — same rows as the first pass (snapshot behaviour; maybe-false `atexit`).
  - `[false]` `[reject]` (Blind Hunter) carried: an unset `PYFORGE_ENVIRONMENT` reads `dev` with no warning — the intent specifies `dev` when unset.
  - `[low]` `[reject]` (Blind Hunter) The OCP doc tells operators to set the `dev` overlay value to `on` and revert — `on` under `dev` is the state the governance rule wants for a new flag, the doc says to revert, and the `PYFORGE_FLAGS_PATH` copy route sits beside it; no harm shown.
  - `[false]` `[reject]` (Blind Hunter) The owning Guild Spec's memlog gets no reconcile entry — the intent forbids editing the Guild Spec or its memlog; `python scripts/spec_surface_reconcile.py` and `pixi run -e pyforge-guild spec-surface-check` exit 0.
  - `[medium]` `[patch]` (Edge Case Hunter) `flip_root`'s overlay is invalid or the second write fails — same defect and fix as the Blind Hunter `flip_root` row.
  - `[low]` `[reject]` (Edge Case Hunter) carried: `configure_file_provider` records the rendered copy as `PYFORGE_FLAGS_PATH` — same as the first row.
  - `[low]` `[reject]` (Edge Case Hunter) A rendered tree written beside `flag-overlays.json` under the name `flags.json` is composed a second time — reachable only by pointing `render --output` at the overlay's directory with the tree's file name; nothing does, and the guard adds a branch.
  - `[false]` `[reject]` (Edge Case Hunter) carried: `tree_view` and `AppConfig.ready()` raise on a bad environment — loud failure is the required behaviour.
  - `[false]` `[reject]` (Edge Case Hunter) `evaluate_cli_boolean` and `render_flag_tree` with no source resolve through `cutover_root.resolve_flags_path`, not the provider's resolver — that order is Story 75.1's fleet contract, which this story must leave unchanged; the platform tests pass an explicit source.
  - `[low]` `[reject]` (Edge Case Hunter) `_three_readings` agrees only with `default=False`; a `DISABLED` flag read with `default=True` differs between the provider and `read_boolean` — the difference is OpenFeature's disabled-returns-default against 75.1's kill-switch-wins, present before this story, and no host caller passes `default=True`.
  - `[maybe-false]` `[reject]` (Edge Case Hunter) carried: the forked-worker `atexit` cleanup could remove a shared render directory — same as the first pass's maybe-false row (would be low if true).
  - `[low]` `[reject]` (Edge Case Hunter) Existing flag tests do not clear an ambient `PYFORGE_ENVIRONMENT` — same as the Blind Hunter row above.
  - `[low]` `[patch]` (Verification Gap) The provider reads a frozen rendered copy after `configure_from_env`; the `resolve_flags_path` docstring promises edits reach it "when it is called again" — verified in the code: with `PYFORGE_FLAGS_PATH` unset, `setdefault` pins it to the copy, which has no sibling overlay, so a later call returns that copy. The checkout-only snapshot behaviour stays as the first pass rejected it (a refresh mechanism, not a correction; in-cluster is polled live); the docstring now says a checkout process restarts to pick up an edit. Docstring-only edit in `django_pyforge/flags.py`.
  - `[medium]` `[patch]` (Verification Gap, other findings) `flip_root` says it validates the overlay before writing and only parses it — same defect and fix as the Blind Hunter `flip_root` row; the test gap named here (only unparseable JSON) is closed by the four new cases.
  - `[false]` `[reject]` (Intent Alignment) The AC naming `pyforge-steward-test` is carried by tests that exercise only the steward extras — the AC asks that the suite pass (exit 0, 1857 passed); the composition, chart and provider ACs are observed at their outermost surfaces in the core and platform suites the spec's Verification section lists.
  - `[false]` `[reject]` (Intent Alignment) carried: production-versus-dev ConfigMaps differing is proven on fixtures — the shipped overlay is identical across environments by the intent's own instruction.
  - `[low]` `[reject]` (Intent Alignment) carried: staging and production are not compared with the tree at landing — same as the first pass's dev-only rows; verified once at landing (9 pairs, 0 differences).
  - `[low]` `[reject]` (Intent Alignment) carried: the chart and Python agree at parsed-JSON equality only — the docs say so.
  - `[false]` `[reject]` (Intent Alignment) The provider and `evaluate_from_source` share one path, so the three readers are not three independent readings — the intent routes both through `pyforge.core.flags`; `read_boolean` over the tree itself is the independent reading, and the tests compare it.
  - `[high]` `[patch]` (Intent Alignment) carried: where `pyforge.core` is not importable the host reads the tree as it is and validates nothing — the first pass's mcp-host sidecar row, already patched with a blocked-import test; the fallback code is present as that row describes.
  - `[medium]` `[patch]` (Intent Alignment) carried: steward maps `FlagConfigError` to the usage code, beyond the intent's text — the first pass's exit-70 row, already patched; `cli.py` still catches it beside `FlagOff`.
  - `[maybe-false]` `[defer]` (Intent Alignment) carried: the helm and `importorskip` gating means the chart and provider tests run only in the platform lane — same as the frontmatter `deferred` entry.

## Auto Run Result

Status: done

### Summary of implemented change

The one flag tree now carries per-environment values. A new value-only document, `src/platform/config/flag-overlays.json`, maps `dev` / `staging` / `production` to variant names of flags the tree defines; it starts with every existing key at its current value, so no evaluated value changes on landing (9 key/environment pairs checked, 0 differences). `pyforge.core.flags` gained the environment (`PYFORGE_ENVIRONMENT`, `dev` when unset, anything else a named error), composition (a `DISABLED` flag stays off everywhere), validation with named errors, and `render(environment) -> bytes`; `read_boolean` reads the composed tree with its signature, resolution order and OFF/absent semantics unchanged. `django_pyforge.flags` configures the host FILE provider from the same rendering and gained `render --environment <env>`. The chart requires `flags.environment` (one of three) and `flags.overlays`, composes and validates in Helm, mounts the rendered tree, and sets `PYFORGE_ENVIRONMENT` on every workload that reads flags. The chart composes the two files itself, so there is no `flags-render` task and `pixi.toml` is unchanged.

### Files changed

- `src/platform/config/flag-overlays.json` — new value-only overlay document.
- `src/shared/packages/pyforge-core/src/pyforge/core/flags.py` — environment, `compose`, `render`, named errors; `read_boolean` reads the composed tree.
- `src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py` — `read_cutover_root` composes the sibling overlay (review patch).
- `src/shared/packages/django-pyforge/src/django_pyforge/flags.py` — provider path through core, `resolve_tree_path`, `render` verb, `ImportError` fallback for images without `pyforge.core`, `OSError` handling.
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` — `FlagConfigError` maps to the usage code (review patch).
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cutover.py` — `flip_root` also sets the target in the overlay (review patch).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` — the kill switch resolves the unrendered tree.
- `src/platform/deploy/charts/platform/{values.yaml,templates/_helpers.tpl,templates/flags-configmap.yaml,templates/NOTES.txt}` — required `flags.environment` / `flags.overlays`, Helm composition, `PYFORGE_ENVIRONMENT`.
- `scripts/flag_gate_check.py` — the overlay is a non-reader, like the tree.
- `.github/workflows/platform-ci.yml`, `.github/workflows/platform-deploy.yml`, the overlay READMEs and values headers, `docs/explanation/platform-deployment-architecture.md`, `docs/how-to/ocp-cluster-bringup.md` — pass the new chart inputs.
- Tests: `pyforge-core` `test_flags.py` and `test_cutover_root.py`; `pyforge-steward` `test_cli.py` and `test_cutover.py`; `pyforge-doctor` `test_flag_kill_switch.py`; `src/platform/tests/test_openfeature_file_flags.py` and `test_chart_invariants.py`; `tests/scripts/test_flag_gate_check.py`.
- Four Spec memlogs (`spec-pyforge-core`, `spec-pyforge-steward`, `spec-pyforge-doctor`, `spec-pyforge-unifying-strategy`) carry surface-reconcile entries naming the governed paths. No `--write-baseline` was passed by me; two scoped stamps the implementation subagent wrote were reverted, so `scripts/.spec-surface-baseline.json` is unchanged from the baseline revision.

### Review findings

43 findings from four layers. Patched: 4 entries (high 2, medium 2, low 4 — by finding rows: 6 high, 6 medium, 7 low).
- Cutover-root divergence (high): `read_cutover_root` composes the overlay; `flip_root` keeps a flip meaning one root everywhere.
- mcp-host sidecar boot crash (high): both host resolvers fall back to the tree as it is when `pyforge.core` is absent.
- Steward exit 70 on a bad environment or overlay (medium): named message and the existing usage code.
- Untested doctor kill-switch resolution (medium): a test that fails when the import is reverted.
- Low: `render --output` `OSError`; the "same bytes" and "every platform pod" doc claims; the OCP bring-up commands missing the chart inputs; the chart environment test now checks every container that mounts the `flags` volume.

Deferred: 1 — helm-gated chart tests may skip in the Platform CI `test` job (maybe-false, medium unverified; `location: .github/workflows/platform-ci.yml`).

Rejected, with the recorded reason (full rows in the Review Triage Log):
- Overlay repeats tree values with no drift check — the intent mandates every key in all three environments.
- Checkout provider serves a snapshot (three findings) — checkout-only, in-cluster is live, fix is a refresh mechanism; documented in the `resolve_flags_path` docstring.
- Go-template composition duplicates Python (two findings) — the intent permits the chart composing; parity tested.
- Staging/production equality with the tree (two findings) — a landing-time property, verified; a standing test would fail when an overlay legitimately differs.
- Host-fetch path unvalidated, `render` positional key, angle-bracket placeholders, duplicated test argv, core test coupling to the platform tree — no harm shown or cosmetic.
- Spec-surface hygiene, `_helm` guard (two findings), unset environment reading `dev`, `tree_view` 500, `ready()` raising, production-versus-dev on fixtures, extra strictness — disproved or intended behaviour.
- `atexit` cleanup in forked workers (maybe-false, low if true) — extra guard for an unshown path.

### Follow-up review recommendation

`followup_review_recommended: true`. Two high entries were patched. The unverified risk: the patch-round code (`flip_root` rewriting `flag-overlays.json`, `read_cutover_root` composing it, and the mcp-host `ImportError` fallback) was written after the adversarial layers ran and has had no independent review, and the mcp-host image was not built — the fallback rests on a blocked-import test and a repro with the mcp-host env's interpreter.

### Verification performed

- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0, 1853 passed, 2 skipped.
- `pyforge-core-test` — exit 0, 2049 passed. `pyforge-doctor-test` — exit 0, 3006 passed, 1 skipped.
- Platform `test_openfeature_file_flags.py` + `test_chart_invariants.py` with `helm` on PATH — exit 0, 153 passed, 0 skipped.
- `lint-types` (ten packages) exit 0; platform `ruff`, `ruff format --check`, `mypy platformapp config tests` exit 0.
- `python scripts/spec_surface_reconcile.py` exit 0; `pixi run -e pyforge-guild spec-surface-check` exit 0; `flag_gate_check` 0 fail.
- `platform-ci-local -- --test`: Django check, ruff, ruff format, mypy, policy suite, sqlmigrate all pass; full suite 968 passed, 1 failed (`test_redis_cache_eviction_broker_survival.py::test_unsplit_redis_loses_broker_state_under_cache_pressure`, a real `redis-server` eviction test; it passed on two of three isolated re-runs, so it is flaky, and this diff touches no cache code).
- `detectors-ci` in a clean shell (`PYTHONSAFEPATH` unset) exits 0 with the dispatch-deployed, gitignored `.claude/skills/caveman/` moved aside (the estate catalog counts it). With it in place, `bmad_estate_check` reds; with `PYTHONSAFEPATH=1`, `pixi_version_check` reds on a sibling import. Neither is this diff.
- After the patch round, `detectors-ci` also reports `ledger-direction` on marshal 74.1: that merge and its ledger promotion are on `main` but not in this branch (`main` moved 45 commits past the base). This diff touches no ledger; it clears when the branch lands. Not fixed here (the ledger is generated).
- Matrix Test Audit: every I/O matrix row has a covering test that ran and passed (core `test_flags.py`, platform host and chart tests).

### Residual risks

- Checkout provider snapshot (a rendered temp copy refreshed only when `resolve_flags_path` is called again) — documented, not fixed.
- The full platform suite ran once after the patch round; the flaky Redis test aside, it is green. The container and promotion stages of `platform-ci-local`, the full `pr-preflight` bundle and the other seven station suites were not run.
- The helm-gated chart tests' CI coverage is unverified (deferred).
- A flip now edits two tracked files (`flags.json` and `flag-overlays.json`); the flip stories 44.4–44.6 are parked, so no live flow exercises it yet.

### Follow-up review pass (2026-09-29)

This pass is the one follow-up the first pass recommended (`followup_pass` = true), run over the diff since `baseline_revision` by four fresh layers. It re-checked the patch-round code the first pass could not review: `flip_root`'s overlay write, `read_cutover_root`'s composition and the mcp-host `ImportError` fallback.

Summary of implemented change: the patch-round code held except one gap. `flip_root` said it validated the overlay before writing either file but only checked that the document parsed; an overlay naming a key the tree lacks, a variant the flag lacks, an unknown environment or an object entry flipped both files and then made every reader refuse. It now composes the overlay it will write (every entry of every environment) first and refuses with `flip refused: <named entry>`, leaving both files untouched. The `resolve_flags_path` docstring also overstated when an edit reaches the FILE provider; it now says a checkout process that ran `configure_from_env` with `PYFORGE_FLAGS_PATH` unset serves a frozen copy until restart (the in-cluster mount is polled live). No behaviour changed beyond the `flip_root` refusal.

Files changed in this pass:

- `src/shared/packages/pyforge-steward/src/pyforge/steward/cutover.py` — `flip_root` composes the overlay before either write.
- `src/shared/packages/pyforge-steward/tests/unit/test_cutover.py` — four refusal cases (unknown key, unknown variant, unknown environment, object entry): the named entry in the message, both files unchanged.
- `src/shared/packages/django-pyforge/src/django_pyforge/flags.py` — `resolve_flags_path` docstring only.
- `spec-pyforge-steward` and `spec-pyforge-unifying-strategy` memlogs — surface-reconcile entries naming the three paths above (appended with `_bmad/scripts/memlog.py`; no `--write-baseline`).

Review findings breakdown: 32 findings (high 1, medium 4, low 15, false 9, maybe-false 3). Patched: 2 entries — medium 1 (`flip_root`, three finding rows) and low 1 (the docstring). Carried from the first pass without re-triage: 15 rows, including the already-patched mcp-host `ImportError` fallback (high) and steward `FlagConfigError` mapping (medium). Deferred: none added (the helm-skip finding is the existing frontmatter entry, `location: .github/workflows/platform-ci.yml`). Rejected, each with its recorded reason in the Review Triage Log: the environment-isolation fixtures (unlikely, three packages), the CD-render value assertion (nothing to assert yet), the required-chart-values upgrade note (the intent requires the value), the `render` verb gaps, the double-compose of a rendered tree beside the overlay, the `default=True` provider difference (pre-existing OpenFeature semantics), the OCP doc edit path, the second-write `OSError` in `flip_root`, and the false findings (docstring scope, owning-Spec memlog forbidden by the intent, resolver order fixed by Story 75.1, provider and CLI reader sharing a path by the intent's own routing).

Follow-up review recommendation: `false`. This was a follow-up pass and it patched no `high`, so the work has converged; patched counts by verdict: medium 1 entry, low 1 entry.

Verification performed:

- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0, 1857 passed, 2 skipped (1853 before; the four new cases).
- The four new `test_cutover.py` cases fail with the `compose` line removed (4 failed, 11 passed) and pass with it (15 passed).
- `python scripts/spec_surface_reconcile.py` — exit 0; `pixi run --frozen -e pyforge-guild spec-surface-check` — exit 0; no `--write-baseline` passed.
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0.
- Not re-run: the platform suite and `detectors-ci` (this pass's only non-test code change is in `pyforge-steward`; the `django_pyforge` change is a docstring). The first pass's platform and detector results stand.
- Ad-hoc `ruff check` on `django_pyforge/flags.py` reports RUF100/I001 findings; the file has no lane (the platform lane lints `src/platform` only, `lint-types` the ten `pyforge-*` packages), the `# noqa: PLC0415` comments follow the package's own convention, and 7 of the 13 findings are on the baseline file.

Residual risks:

- The checkout provider snapshot is unchanged and now documented accurately: a host started in a checkout does not see a tree or overlay edit until restart. The kill switch and a `flip_root` reach a running in-cluster provider (live mount), not a checkout one.
- `flip_root` still writes the tree and the overlay as two atomic writes, not one; a failure between them leaves the tree flipped and the overlay pinning the old root. The flip stories 44.4–44.6 are parked, so no live flow exercises it.
- The helm-gated chart tests' CI coverage is unverified (the frontmatter `deferred` entry).
