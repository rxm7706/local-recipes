---
title: "76.4: The pyforge.three_surfaces demo flag leaves the tree"
type: 'chore'
created: '2026-09-28'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: flag-infrastructure
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/platform/config/flags.json
  - src/shared/packages/django-pyforge/src/django_pyforge/flags.py
  - src/shared/packages/django-pyforge/src/django_pyforge/apps.py
  - src/platform/tests/test_openfeature_file_flags.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-76-2-every-flag-in-the-tree-carries-its-owner-story-and-cleanup-clock-in-flagd-metadata.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pyforge.three_surfaces` entered `src/platform/config/flags.json` with Story 26.4 (`7a194d3f57`,
2026-08-25) to prove that one FILE tree flips Django, MCP and the CLI. No production code reads it. It has read `on`
in every environment since it entered, so its 90-day clock (`spec-feature-flag-governance` Q4) runs out on
2026-11-23, and Q4 asks the flag's owner to file its removal story. The operator ruled on 2026-09-28 (night): remove
it; do not keep it as a kill switch. Steward owns the flag, so this is that story.

The flag is not only an entry in the tree. `django_pyforge/flags.py` names it as `FLAG_KEY` (measured at
`0c8c07e6fc`):

- `FLAG_KEY` is the default key of `evaluate_boolean`, `evaluate_from_source`, the MCP `get_flag` tool, and the
  optional positional of `python -m django_pyforge.flags`.
- `wait_until_ready` probes `FLAG_KEY` with `get_boolean_details` inside every `configure_file_provider` call.
  `apps.py`'s `ready()` runs `configure_from_env` at host startup, so if only the tree entry were removed, every
  host start would wait 8 s and raise `FILE provider not ready` (each probe returns `FLAG_NOT_FOUND`).
- `src/platform/tests/test_openfeature_file_flags.py` imports `FLAG_KEY` to build its temporary flagd trees.

**Approach:**

- Remove the `pyforge.three_surfaces` entry from `src/platform/config/flags.json`, with its flagd `metadata` if Story
  76.2 has written it. Remove its entry from `src/platform/config/flag-overlays.json` too, if Story 76.1 put one
  there.
- In `django_pyforge/flags.py`, remove `FLAG_KEY`:
  - `evaluate_boolean`, `evaluate_from_source` and the MCP `get_flag` tool take `key` as a required argument, and
    `python -m django_pyforge.flags` takes it as a required positional.
  - `wait_until_ready` stops probing a named flag. It waits until `api.get_client().get_provider_status()` reads
    `ProviderStatus.READY` (openfeature-sdk 0.10.0, the platform pin), raises the same named `RuntimeError` on
    `ERROR`, `FATAL` or its timeout, and keeps its `timeout_s` signature.
  - If the flagd in-process FILE provider reports `READY` before the tree is readable, prove it with a test that
    fails first. Then fall back to probing the first key of the tree being configured, read from that file, with a
    type-matched `get_*_details` call. Record the choice in the story's result. Either way, no flag key is written
    into the module.
- Re-key `test_openfeature_file_flags.py` to a test-local constant such as `_FIXTURE_KEY = "pyforge.test.fixture"`.
  These tests prove the FILE machinery (Django, MCP and the CLI agree, the host fetch, no egress, a live file change,
  forbidden anonymous views, one tree under `src/platform`) and they all stay. Add a test that configures the real
  tree after the removal: it holds `pyforge.cutover_root` and no boolean flag. `configure_file_provider` returns, and
  `evaluate_cutover_root` reads `local-recipes`.
- Change the `--flag` help example of `doctor flags kill-switch` (`pyforge-doctor/src/pyforge/doctor/__main__.py`,
  `help="OpenFeature flag key to disable (e.g. pyforge.three_surfaces)"`) to a neutral example that names no key in
  the tree: `(e.g. pyforge.<station>.<capability>)`. After the removal, the old example would point an operator at a
  key that no longer exists. *(Folded in 2026-09-29, coordinator ruling.)* `tests/unit/test_flag_kill_switch.py`
  keeps `pyforge.three_surfaces` as its key: the test writes its own temporary flags file and reads no real tree, so
  the name there is an arbitrary fixture string, not a consumer. `spec-pyforge-doctor` governs that path, so it is
  reconciled and stamped with the rest.
- Leave `pyforge.cutover_root` and the rest of the machinery as they are: the chart's flags ConfigMap,
  `tree_view`/`eval_view`, the `flags` MCP face, `evaluate_cutover_root`, and the 76.1 renderer and 76.2 metadata
  check.

Ledger key: `76-4-the-pyforge-three-surfaces-demo-flag-leaves-the-tree`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: chore / S / S-76.2.

### Living CAP citations

- `spec-feature-flag-governance` CAP-5 (the flag platform is steward's) and Q4 (a flag lives 90 days after it is ON
  everywhere; the owning station files the removal story). No steward CAP and no station FR are minted (the 76.1–76.3
  precedent).
- canopy:AD-11: one tree, one provider, no egress. The removal keeps all three.

## Acceptance Criteria

- Given `src/platform/config/flags.json` When it is read Then it has no `pyforge.three_surfaces` key and still defines `pyforge.cutover_root` unchanged; `flag-overlays.json`, if present, names no `pyforge.three_surfaces`
- Given `rg -n 'pyforge\.three_surfaces' src/platform src/shared/packages/django-pyforge src/shared/packages/pyforge-core src/shared/packages/pyforge-doctor/src` When it runs Then it finds nothing, and `django_pyforge.flags` defines no `FLAG_KEY`
- Given `pyforge doctor flags kill-switch --help` When it prints Then the `--flag` example reads `pyforge.<station>.<capability>`, and `tests/unit/test_flag_kill_switch.py` still passes with its own temp-tree key
- Given a tree holding only the string flag `pyforge.cutover_root` When `configure_file_provider` configures it Then it returns within its timeout, raises nothing, and names no flag key while it waits
- Given a tree the provider cannot load When `configure_file_provider` configures it Then it raises the named `RuntimeError` after `timeout_s`, as it does today
- Given the host starting against the real tree When `DjangoPyforgeConfig.ready()` runs Then it completes and `evaluate_cutover_root()` returns `local-recipes`
- Given `evaluate_boolean`, `evaluate_from_source`, `get_flag` or `python -m django_pyforge.flags` called without a key When it runs Then it refuses (a `TypeError`, a tool-schema error, or an argparse exit 2), rather than quietly reading a key that is not in the tree
- Given `test_openfeature_file_flags.py` re-keyed to a test-local fixture key When the platform suite runs Then every test that passed before still passes: Django, MCP and CLI agree, the host fetch, no egress, a live file change is seen, anonymous views are forbidden, and there is one tree under `src/platform`
- Given the change When `pixi run --frozen -e pyforge-steward pyforge-steward-test` runs Then it passes

## Boundaries & Constraints

**Always:**
- Keep one tree, one provider, no egress (canopy:AD-11). Readiness still comes from the in-process FILE provider;
  nothing starts a daemon or makes a network call to decide it.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every Spec `spec-surface-check` names: the platform and chrome Specs that govern `src/platform/` and
  `django-pyforge`, and `spec-pyforge-doctor` for `__main__.py`. Stamp each scoped with `--spec`.

**Never:**
- Do not remove or rename `pyforge.cutover_root`, the chart's flags ConfigMap, the `flags` MCP face or
  `evaluate_cutover_root`.
- Do not start before Story 76.2 has landed (`Deps: S-76.2`). Removing the flag first would leave 76.2's metadata AC
  naming a key that is gone.
- Do not edit `pyforge-doctor` beyond that one help string. Its kill-switch tests keep their temp-tree key, and the
  actuator's behaviour does not change.
- Do not edit the done story specs `spec-26-4-…` or `spec-48-5-…`, or the Guild Dream. They keep the name as
  history.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| real tree after removal | `pyforge.cutover_root` only | provider ready; host starts; cutover root `local-recipes` | — |
| empty tree | `{"flags": {}}` | ready once the provider reports it (on the fallback path, once the file parses); no key probed | — |
| boolean-only fixture tree | `pyforge.test.fixture` on/off | the FILE-machinery tests evaluate it as before | — |
| unreadable tree | a malformed JSON file | the named `RuntimeError` after `timeout_s` | as today |
| no key given | `evaluate_boolean()` / CLI with no positional | refused | `TypeError` / argparse exit 2 |
| overlay names the key | `flag-overlays.json` carries `pyforge.three_surfaces` | the entry is removed with the flag | 76.1's validation would otherwise refuse an unknown key |

</intent-contract>

## Source

Contract authored from the operator's ruling of 2026-09-28 (night), recorded in `spec-pyforge-steward`'s `.memlog.md`
and in `docs/governance/spec-feature-flag-governance/.memlog.md`, from `spec-feature-flag-governance` CAP-5 and Q4, and
from the grep of the tree recorded in the steward memlog's direction entry of the same night.

## Binding

Parent Spec capability: `spec-feature-flag-governance` CAP-5 (the Guild's Spec; no station CAP or FR is minted).
Dream: `docs/dreams/feature-flag-governance.md`.
Ledger key: `76-4-the-pyforge-three-surfaces-demo-flag-leaves-the-tree`.
Ledger status at mint: `backlog`.
Deps: S-76.2 (the operator asked for this story to run after the metadata story).
Flag: `flag-exempt: flag-infrastructure` (it removes a flag from the one tree and keeps the provider working; nothing
new ships behind a flag).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild platform-ci-local -- --test` — expected: `test_openfeature_file_flags.py` passes,
  re-keyed, with the new real-tree and readiness tests.
- `rg -n 'pyforge\.three_surfaces' src/platform src/shared/packages/django-pyforge src/shared/packages/pyforge-core src/shared/packages/pyforge-doctor/src`
  — expected: no match.
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the help string changed; the kill-switch
  tests keep their temp-tree key).
- `pixi run -e pyforge-guild detectors-ci` — expected: no new findings.

## Review Triage Log
