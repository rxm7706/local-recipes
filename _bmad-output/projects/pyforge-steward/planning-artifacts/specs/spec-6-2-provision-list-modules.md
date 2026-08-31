---
title: 'provision --list-modules'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-module-provisioning/SPEC.md']
warnings: ['oversized']
baseline_revision: 'e3487fce205fbfa5c86de6575e196c00cfa5d675'
final_revision: '6f2a86fc1b9c6b28079e250fed1e08caedb545e2'
---

<intent-contract>

## Intent

**Problem:** Story 6.1 added `_SUPPORTED_MODULES` and `steward provision --module <name>`, but there is no read path for it — an operator must already know a module's exact registered name and current install state before choosing one; nothing lets them discover the supported set or which are already provisioned first.

**Approach:** Add `steward provision --list-modules [--json]`, a new sibling flag on the existing `provision` duty, that derives each registered module's `installed`/`available` state directly from the filesystem (`_bmad/config.yaml`'s own top-level keys — the exact anti-zombie key `merge-config.py` writes) — no new state file, matching `--list`'s own read-only, pixi.toml-derived precedent (CAP-2, FR-20).

## Boundaries & Constraints

**Always:**
- Every reported state is derived by reading the filesystem at call time (`_SUPPORTED_MODULES`'s registered names + `_bmad/config.yaml`'s top-level keys) — never a hand-maintained "installed" list and never a new state file (derive-don't-declare, matches `--list`'s own precedent).
- A module reports `"installed"` iff its registered name is a top-level key in `_bmad/config.yaml` — the exact key `merge-config.py`'s own anti-zombie `config[module_code] = ...` writes (verified against the real script); otherwise `"available"`.
- `--list-modules` never writes to `_bmad/config.yaml` or any other file — read-only, mirrors `_run_list`'s own `pixi.toml` never-writes guard.
- `--json` is honored on `--list-modules`'s success path (mirrors `format_environments`'s `as_json` split) and on its error path via the existing `_render_error` (mirrors the `--list --json` malformed-`pixi.toml` regression guard from Story 3.3).
- `--list-modules` lands as the new top-precedence flag in `ProvisionDuty.run()`'s if-chain, ahead of `--module` — the documented convention that each new story's flag lands at the top.

**Block If:** None identified — the state vocabulary (`installed`/`available`, matching CAP-2's own wording) and the derivation key (`_bmad/config.yaml`'s top-level module-code key) are both resolved above with evidence from the real `merge-config.py` source.

**Never:**
- Does not read or run any module's own installer/setup scripts to determine state — a pure filesystem read, no subprocess call (unlike `--module`).
- Does not add a third state for "registered but its backend/pixi dependency isn't materialized" — `provision_module` already reports that distinctly (`FileNotFoundError`) the moment someone tries to provision; this story's own AC and CAP-2 name only the two-state "installed vs merely available" split.
- Does not perform deep post-install verification (e.g. confirming the module is actually importable/wired) — that is Story 6.3's scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No `_bmad/config.yaml` | fresh checkout, `bmb` registered, config.yaml absent | `bmb: available` | No error expected |
| `_bmad/config.yaml` has a `bmb:` key | file contains a `bmb:` section (written by a prior `--module bmb` run) | `bmb: installed` | No error expected |
| `--list-modules --json` | any state | `{"bmb": "installed"}` or `{"bmb": "available"}` | Same JSON shape on any failure path |
| Malformed `_bmad/config.yaml` | file exists, not valid YAML | `DutyResult(ok=False, ...)` naming the parse failure, `--json` honored | `yaml.YAMLError`, caught at `ProvisionDuty`'s existing boundary |
| `_bmad/config.yaml` parses to a non-mapping (e.g. a bare list) | malformed but valid YAML | Treated as no modules installed — every registered module reports `available` | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- add `module_install_states()`, `format_module_states()`, `_run_list_modules()`; wire into `ProvisionDuty.run()` as new top precedence
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- add `--list-modules` to `_add_provision_subparsers`; extend `--json` help text
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_list_modules.py` -- new, mirrors `test_provision_list.py`'s shape
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/{spec-bmad-module-provisioning,spec-pyforge-steward}/.memlog.md` -- append `(change)` entries naming every touched file (S-13.2 per-file reconciliation; Story 6.1's own repair-pass precedent)

## Tasks & Acceptance

**Execution:**
- [x] `provision.py` -- add `module_install_states(*, cwd: str | Path) -> dict[str, str]`: read `_bmad/config.yaml` if present (`yaml.safe_load`; treat a missing file or a parse result that isn't a `dict` as `{}`), return `{name: "installed" if name in config else "available" for name in _SUPPORTED_MODULES}`
- [x] `provision.py` -- add `format_module_states(states: dict[str, str], *, as_json: bool) -> str` mirroring `format_environments`: JSON -> `json.dumps({name: states[name] for name in sorted(states)}, indent=2)`; text -> aligned `name  state` lines sorted by name, or `"provision --list-modules: no modules registered"` when empty
- [x] `provision.py` -- add `_run_list_modules(ns) -> DutyResult` calling `module_install_states(cwd=repo_root())` then `format_module_states(..., as_json=getattr(ns, "json", False))`; wire as the new first check in `ProvisionDuty.run()`, ahead of `--module`; update the class docstring's precedence line and `_PROVISION_HELP`
- [x] `cli.py` -- add `provision_parser.add_argument("--list-modules", action="store_true", help="list every registered module with installed/available state (derived from the filesystem)")`; update the `--json` argument's help text to mention `--list-modules`; update `_add_provision_subparsers`'s docstring
- [x] `tests/conformance/test_provision_list_modules.py` -- cover every I/O Matrix row (no config.yaml, `bmb` key present, `--json`, malformed YAML honors `--json` on error, non-mapping config.yaml degrades to all-available) plus a read-only guard (`_bmad/config.yaml` byte-identical before/after) and a precedence test (`--list-modules` wins over `--module`/`--verify`/`--list`)
- [x] Append one `(change)` memlog entry to each of `spec-bmad-module-provisioning` and `spec-pyforge-steward` naming every file this story touches (S-13.2; mirrors Story 6.1's own repair-pass entries)

**Acceptance Criteria:**
- Given the registered module set (`bmb`), when `steward provision --list-modules` runs, then every registered module is listed with its state derived from `_bmad/config.yaml`'s own top-level keys, never from a hand-maintained list
- Given `_bmad/config.yaml` does not exist, when `steward provision --list-modules` runs, then every registered module reports `available` and no error occurs
- Given `--list-modules --json` against a malformed `_bmad/config.yaml`, when the command runs, then the result is a parseable JSON error object honoring `--json`, matching `--list --json`'s own existing precedent
- Given `--list-modules` and `--module`/`--verify`/`--list`/`--runner`/`--env` are all passed together, when `ProvisionDuty.run()` dispatches, then `--list-modules` wins (new top precedence)
- Given any state, when `steward provision --list-modules` runs, then `_bmad/config.yaml` (and every other file) is left byte-for-byte unchanged

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4 (high 0, medium 1, low 3)
- defer: 1
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` A `_bmad/config.yaml` with invalid UTF-8 bytes raised an uncaught `UnicodeDecodeError` past `ProvisionDuty.run()`'s exception boundary, crashing to a raw traceback / `EXIT_INTERNAL` instead of a clean `DutyResult` — verified directly (reproduced the crash before fixing). Widened the except tuple to catch `UnicodeDecodeError`, matching the file's own precedent of widening this tuple as new failure modes are discovered (Story 6.1 added `yaml.YAMLError` the same way); added a CLI-level regression test proving `--json` now honors this error path too.
  - `[low]` `[patch]` The new `# ── Module discovery (FR-?, ...)` section comment carried an unfilled `FR-?` placeholder — filled with the actual PRD ID, `FR-20`.
  - `[low]` `[patch]` No test covered an empty/comment-only `_bmad/config.yaml` (`yaml.safe_load` → `None`, a distinct branch from "parses to a non-dict") — added `test_module_install_states_empty_config_yaml_degrades_to_all_available`.
  - `[low]` `[patch]` No test covered `format_module_states`'s sort/alignment behavior with 2+ entries — added `test_format_module_states_text_aligns_multiple_names_sorted` and `test_format_module_states_json_multiple_names_sorted`.

Rejected (verified, not fixed): `module_install_states` reports `installed` from key presence alone without validating the value looks like `merge-config.py`'s own `module_section` dict shape — by design, per this spec's own Design Notes evidence trail; deeper validation is Story 6.3's declared scope ("exited 0 but left the module unimportable"), and the only way to produce a differently-shaped value is hand-corrupting `_bmad/config.yaml` outside any real code path this story wraps. Same reasoning for the claim that `--list-modules` should cross-reference the module's backend `skill_dir` (a third state) — explicitly rejected by this spec's own "why two states, not three" Design Note. The precedence test hand-builds an `argparse.Namespace` instead of going through real argparse — matches `test_provision_module.py`'s own existing `test_provision_module_takes_precedence_over_verify_and_list` precedent verbatim, not a gap. A `_bmad/config.yaml` key differing only in case (`BMB` vs `bmb`) reporting `available` — not reachable via any real code path: `module.yaml`'s own `code:` field is fixed lowercase and never case-transformed anywhere in the pipeline; only manual file corruption could produce it. `--list-m` becoming an ambiguous argparse abbreviation against `--list`/`--list-modules` — real but low-consequence (a clear "ambiguous option" argparse error, not silent misbehavior), and the proposed `allow_abbrev=False` fix is a repo-wide parser change with blast radius disproportionate to an XS story. One reviewer's claim that no "story spec Design Notes" file exists anywhere in the checkout (and that `implementation-artifacts/` doesn't exist) is factually false — verified directly: `_bmad-output/implementation-artifacts/spec-6-2-provision-list-modules.md` and `spec-6-1-provision-module-name.md` both exist with populated `## Design Notes` sections; likely a verification failure in that reviewer's own environment (the Tier-3 backlink resolves outside this worktree).

Deferred: the parent capability spec `spec-bmad-module-provisioning/SPEC.md` still has `status: draft` and an unresolved `open_questions` entry about installed-vs-available design, even though this story (plus Story 6.1) has now shipped 2 of its 3 capabilities and concretely resolved that exact open question. Pre-existing since Story 6.1 (which also didn't update either field); fixing it means deciding how/when a capability-spec's own status/open_questions should move as child stories land incrementally, which is bigger than this XS story's scope. Logged to `deferred-work.md`.

## Design Notes

**Why `_bmad/config.yaml` top-level key membership, not a fresh call into `provision_module`'s own validation:** `merge-config.py`'s `merge_config()` unconditionally does `config[module_code] = module_section` (verified by reading the real script under `.pixi/envs/local-recipes/share/bmad-builder/skills/bmad-bmb-setup/scripts/merge-config.py`), so key presence is both the exact write target and a pure read with no subprocess involved — no need to re-derive `module.yaml`'s own `code:` field at list time, since `_SUPPORTED_MODULES`'s registered names are already verified to match it (Story 6.1's own `RuntimeError` guard).

**Why two states, not three:** CAP-2 (`spec-bmad-module-provisioning`) and Story 6.2's own AC both say "installed vs merely available" / "installed state" — a binary split. A missing backend directory (the pixi dependency not materialized) is already a distinct, well-reported failure mode at `--module` time (`FileNotFoundError` naming the exact fix); duplicating that as a third list-time state would be undeclared scope for an XS-effort story.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (real backend, no mocks):**
- From repo root, with `local-recipes` on PATH: `pixi run -e pyforge-steward steward provision --list-modules` before and after `pixi run -e pyforge-steward steward provision --module bmb`, confirm the reported `bmb` state flips from `available` to `installed`.

## Auto Run Result

- **Summary:** `steward provision --list-modules [--json]` added as the new top-precedence
  `provision` flag (ahead of `--module`). `module_install_states()` derives each registered
  module's `installed`/`available` state purely from `_bmad/config.yaml`'s own top-level
  keys — the exact anti-zombie key `merge-config.py`'s own `config[module_code] = ...`
  writes — no subprocess call, no new state file (derive-don't-declare). A missing
  `_bmad/config.yaml`, or one parsing to a non-mapping, both degrade to "all available"
  rather than erroring; a genuinely malformed or invalid-encoding file propagates to
  `ProvisionDuty.run()`'s existing exception boundary and honors `--json` on error.
  `format_module_states()` mirrors `format_environments`'s text/JSON split. Review pass on
  2026-08-09 found 4 patch findings (0 high, 1 medium, 3 low), all fixed; 1 item deferred
  (parent `spec-bmad-module-provisioning/SPEC.md`'s stale `status`/`open_questions`,
  pre-existing since Story 6.1); 6 findings rejected as verified non-issues (including one
  reviewer's factually-incorrect claim that no story-spec Design Notes exist in this
  checkout).
- **Files changed:**
  - `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- new
    `module_install_states()`, `format_module_states()`, `_run_list_modules()`; wired as
    the new top-precedence check in `ProvisionDuty.run()`; widened the exception boundary
    with `UnicodeDecodeError` (review patch); `FR-20` filled into the new section comment
    (review patch).
  - `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- new
    `--list-modules` flag; extended `--json`'s help text.
  - `src/shared/packages/pyforge-steward/tests/conformance/test_provision_list_modules.py`
    (new) -- 22 tests covering every I/O-matrix row, a read-only guard, the precedence
    check, and the review pass's 5 new regression tests (empty-config-yaml, multi-entry
    sort/alignment x2, invalid-encoding primitive + CLI round-trip).
  - `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/{spec-bmad-module-provisioning,spec-pyforge-steward}/.memlog.md`
    -- one `(change)` entry appended to each, naming every touched file (S-13.2).
  - `_bmad-output/implementation-artifacts/deferred-work.md` -- one new entry for the
    deferred finding above.
- **Review findings breakdown:** patch 4 (fixed: exception-boundary widening, `FR-20`
  placeholder fill, 2 test-coverage gaps closed with 5 new tests); defer 1 (parent SPEC.md
  staleness, logged); reject 6 (verified non-issues, see Review Triage Log for full
  reasoning per finding).
- **Follow-up review recommendation:** `false` -- 4 localized, low/medium-severity patches
  (one exception-type widening matching an established file-local pattern, three additive
  test-coverage fixes), no behavior/API/data-model change beyond strictly improved error
  handling on an already-narrow failure path.
- **Verification performed:** `pixi run --frozen -e pyforge-steward pyforge-steward-test`
  -- 253 passed (248 pre-review + 5 new regression tests). `python3
  scripts/spec_surface_check.py` -- exit 0, "OK: every tracked file governed or
  allowlisted; no drift."
- **Residual risks:** the spec's own "Manual checks" (real `bmb` pixi backend / `uv` on
  PATH) were not run in this unattended session, consistent with the spec marking them
  manual rather than a gating verification command -- same posture Story 6.1's own dev
  session took. The deferred parent-SPEC.md staleness (above) means an operator reading
  `spec-bmad-module-provisioning/SPEC.md` in isolation would not yet see it reflect that
  CAP-1/CAP-2 are shipped or that the installed-vs-available design question is resolved
  -- the `.memlog.md` entries are the accurate record in the interim.
