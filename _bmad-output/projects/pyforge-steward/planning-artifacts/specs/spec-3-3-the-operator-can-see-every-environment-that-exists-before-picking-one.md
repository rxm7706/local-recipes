---
title: 'Story 3.3: The operator can see every environment that exists, before picking one'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-steward/implementation-artifacts/spec-3-1-any-named-pixi-environment-materializes-with-one-command.md']
warnings: []
---

<intent-contract>

## Intent

**Problem:** Discovering what environments exist in `pixi.toml`'s `[environments]` table today means reading raw TOML by hand.

**Approach:** `format_environments` — read-only text/`--json` rendering of Story 3.1's own `load_pixi_environments` output. No new data-gathering primitive; this story only shapes what 3.1 already reads. Wired as `steward provision --list [--json]`.

## Boundaries & Constraints

**Always:**
- Read-only — `--list` never writes to `pixi.toml` (AD-5), proven by a dedicated test that snapshots the file's bytes before/after the CLI call.
- `--json` output is sorted by environment name (deterministic, diff-friendly).

**Block If:** none — `--list` has no failure mode of its own beyond `load_pixi_environments`'s existing `FileNotFoundError`/`TOMLDecodeError` propagation (Story 3.1).

**Never:**
- No filtering/hiding of any environment — every key in `[environments]` is listed, including ones with no `pyforge-*`/BMAD-project counterpart (e.g. `linux`, `build`, `vuln-db`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Ordinary `pixi.toml` (~19 entries) | `--list` | Every name listed with its composing features, aligned text table | No error |
| `--json` passed | `--list --json` | Same data as a sorted JSON object, `{name: [features...]}` | No error |
| No environments (degenerate/malformed-but-parseable manifest) | empty `[environments]` table | Clear "no environments found" sentence (text) / `{}` (JSON) — never a blank string | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- EDIT: `format_environments`, `_run_list`, `ProvisionDuty.run` gains the `--list` branch
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- EDIT: `--list`/`--json` flags (declared alongside `--env`/`--runner` in Story 3.1's `_add_provision_subparsers` edit)
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_list.py` -- NEW: full I/O matrix, primitive + CLI level, incl. a read-only proof

## Tasks & Acceptance

**Execution:**
- [x] `provision.py` -- `format_environments(environments, *, as_json) -> str`
- [x] `provision.py` -- `_run_list`; `ProvisionDuty.run` dispatches `--list`
- [x] `cli.py` -- `--list`/`--json` flags
- [x] `tests/conformance/test_provision_list.py` -- full matrix incl. `test_provision_list_never_writes_to_pixi_toml`

**Acceptance Criteria:**
- Given repo-root `pixi.toml`'s current `[environments]` table (~14 entries — confirmed live at 19), when `steward provision --list` is run, then every environment name is listed with its composing `features` list, read-only.
- Given `--json` is passed, when `steward provision --list --json` is run, then the same data is emitted as machine-readable JSON.

## Review Triage Log

### 2026-08-07 — Self-review (adversarial re-read before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- **Checked**: `format_environments` performs zero I/O of its own — it is a pure function over the `dict[str, tuple[str, ...]]` `load_pixi_environments` already produced, confirmed by inspection (no `open`/`Path`/`subprocess` reference anywhere in the function body).
- **Checked**: the empty-input degrade for BOTH renderings — `{}` (a valid, parseable empty JSON object, not an error) for `--json`, and a plain, non-blank sentence for text — covered by `test_format_environments_empty_text_is_a_clear_sentence_not_a_blank_string` / `test_format_environments_empty_json_is_an_empty_object`.
- **Checked**: no docstring-vs-behavior drift — `format_environments`'s docstring claims JSON output is "sorted by name"; `test_format_environments_json_emits_machine_readable_data` asserts the parsed dict's content (dict equality is order-independent in Python, so this alone doesn't PROVE ordering) — the sortedness claim is instead proven structurally by `format_environments`'s own implementation (`sorted(environments)` used as the dict-comprehension's iteration order) rather than a brittle string-ordinal assertion on JSON text, which `json.dumps`'s own key ordering already guarantees preserves insertion order.

**Follow-up review recommendation: false** — a pure rendering function over an already-tested data source (Story 3.1); no new I/O surface to get wrong.

## Design Notes

**Why "~14 entries" in the AC undercounts the live repo.** Confirmed live: `pixi.toml`'s `[environments]` table currently has 19 entries (`linux`, `osx`, `win`, `build`, `grayskull`, `conda-smithy`, `local-recipes`, `vuln-db`, `gcloud`, `pyforge-ci`, `pyforge-warden`, `pyforge-atlas`, `pyforge-doctor`, `pyforge-scribe`, `bmad-ui`, `pyforge-herald`, `pyforge-mason`, `pyforge-steward`, `pyforge-marshal`). The AC's "~14" is an approximate figure from when this epic was planned and has since drifted upward as new `pyforge-*` stations were added — `--list` reads the table LIVE on every invocation, so this drift self-corrects at runtime without any code change; the spec text is not re-derived from a stale count anywhere in `provision.py`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- expected: all tests pass
- `pixi run --frozen -e pyforge-steward steward provision --list` / `--list --json` -- expected: real repo-root environments printed

**Results (2026-08-07):**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- 161 passed (full Epic 3 suite; this story's own share is `test_provision_list.py`'s 8 tests).
- **Live verification (real, not faked):** `steward provision --list` printed all 19 real environments with their real composing features (e.g. `local-recipes    python, build, grayskull, conda-smithy, local-recipes`); `steward provision --list --json` emitted valid JSON with the same 19 keys, verified by piping through the transcript's own real output.

## Adversarial review pass (2026-08-07, Blind Hunter + Edge Case Hunter)

Dispatched with the diff file path only, no shared context.

- `medium` `patch` **`--list --json` on an error path emitted plain text, not JSON.** `_run_list` only wrapped the SUCCESS case in `format_environments(..., as_json=...)`; any error raised inside (a malformed `pixi.toml`, a missing `pixi.toml`, a `repo_root()` failure) propagated to `ProvisionDuty.run`'s generic exception handlers, which built the summary as plain text (`f"provision: {exc}"`) regardless of whether `--json` was passed -- `cli.main()` has no JSON-aware rendering anywhere in its dispatch path, so a caller that unconditionally `json.loads()`s the output after passing `--json` (the whole point of the flag) crashed on any error. Fixed: a new `ProvisionDuty._render_error` helper checks `ns.json` and emits `{"error": message}` when set -- applied uniformly to BOTH exception handlers (`subprocess.CalledProcessError` and the general `(RuntimeError, FileNotFoundError, tomllib.TOMLDecodeError)` catch), so every flag's error path, not just `--list`'s, now honors `--json`. New test: `test_provision_list_json_on_malformed_pixi_toml_still_emits_valid_json`.

**Re-verification (2026-08-07, after the patch):** `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- **162 passed** (full suite).

**Follow-up review recommendation (updated): false** -- narrow fix, covered by a dedicated regression test.
