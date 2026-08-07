<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-07 -->
---
title: 'Story 1.5: The operator can see every credential Steward knows about, never a secret value'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** There is no way to see the whole credential picture Steward knows about in one place — Story 1.4 created `.steward/keys-inventory.yaml` and writes to it, but nothing reads it back for the operator. The alternative today is grepping env vars and Dream files, exactly the gap this epic exists to close.

**Approach:** Add `steward keys list [--inventory <path>] [--json]`, a thin read+format over Story 1.4's `load_inventory`. Text mode prints a one-line-per-identity table (name, scope, provenance, status, last_rotated); `--json` prints the same fields as a JSON array. Both formats read `KeyIdentityEntry` fields only — never anything derived from opening an identity file or a `.age` payload — so a raw secret value structurally cannot appear in either format, closing FR-5/NFR-7 as a regression-tested invariant, not just a code-review claim.

## Boundaries & Constraints

**Always:**
- `list` reads the inventory via `load_inventory` only — it never opens/reads an `identity_path` file or a path listed in `secrets` (those are pointers Story 1.4 already established are never secret CONTENT themselves, but `list`'s own job is display, not verification — it must never dereference them at all).
- Every field `list` prints comes directly from a `KeyIdentityEntry`'s existing fields (`name`, `scope`, `provenance`, `status`, `last_rotated`, `identity_path`, `secrets`) — no new field is invented, and `identity_path`/`secrets` are filesystem POINTERS, already established in Story 1.4's Design Notes as safe to display (never key material).
- A dedicated `tests/meta/`-tier test (mirrors the story's own AC wording, NFR-7) asserts across BOTH `--json` and default-text output that a real secret-shaped string planted inside an identity file's content never appears in `list`'s output — proving by execution, not just by code inspection, that `list` never dereferences the pointer.
- `provenance` is displayed verbatim for both `"issued"` (Steward-minted, Story 1.4) and `"observed"` (pre-existing repo credential Steward did not create) entries — `load_inventory`/`save_inventory` (Story 1.4) already accept both values; this story adds no new write path, only proves `list` renders both correctly. An `observed` entry is added to the inventory by hand-editing the YAML (or, later, by Story 1.6's auditor) — this story's own tests construct one directly via `save_inventory`, the same precedent Story 1.4 set for constructing pre-existing entries.
- `--json`/text output is deterministic in entry order (inventory file order, which is itself insertion order from `save_inventory`) — no hidden sort that could make two identical inventories print differently.

**Block If:** none — read-only display work, no ambiguous external decision points.

**Never:**
- No new inventory write path — `list` is read-only. Creating an `observed` entry via a dedicated CLI verb is explicitly Story 1.6's ("auditor-populated") concern, not this story's.
- No `keys audit` verb — Story 1.6.
- No revocation — Story 1.7.
- No pagination/filtering flags (`--scope`, `--status`) — not named by this story's AC; adding them now would be speculative surface ahead of any story that asks for it.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Issued + observed entries, text mode | Inventory with one `issued` and one `observed` entry | Both rows printed; each row's `provenance` column shows its own value | No error expected |
| Issued + observed entries, `--json` | Same inventory | A JSON array with one object per entry, `name`/`scope`/`provenance`/`status`/`last_rotated`/`identity_path`/`secrets` keys | No error expected |
| Secret-shaped identity file content | An entry whose `identity_path` points at a file containing a real-looking secret string | That string never appears anywhere in `list`'s stdout, in EITHER format | No error expected — proven by execution |
| Empty inventory | No `.steward/keys-inventory.yaml`, or an empty `identities` list | A clear "no identities" message (text) / `[]` (`--json`); exits `EXIT_OK` | No error expected |
| Missing `--inventory` flag | No `--inventory` given | Defaults to `default_inventory_path()` (Story 1.4's repo-root resolver) | No error expected |
| Malformed inventory file | A file that fails `load_inventory`'s validation | `InventoryError` propagates | `DutyResult(ok=False, ...)` via CLI (`EXIT_FAILED`) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` -- add `format_inventory(entries, *, as_json) -> str`; extend `KeysDuty`'s `_KEYS_VERBS`/`run` with `list`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- add `keys list [--inventory] [--json]` subparser; extend `_KEYS_VERBS`/`_HELP["keys"]`
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_list.py` -- NEW: covers the I/O matrix, both at the primitive (`format_inventory`) and CLI level
- `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` -- add `test_keys_list_output_never_contains_a_planted_secret_value` (NFR-7, the story's own explicit "dedicated tests/meta/ test" requirement)

## Tasks & Acceptance

**Execution:**
- [x] `keys.py` -- add `format_inventory(entries, *, as_json: bool) -> str` -- JSON: `json.dumps` of one dict per entry (all `KeyIdentityEntry` fields); text: a simple aligned table, `"no identities in the inventory"` when empty
- [x] `keys.py` -- extend `KeysDuty`'s `_KEYS_VERBS`/`run` with `list` -- reads via `load_inventory`, formats via `format_inventory`, catches `ValueError`/`InventoryError` the same way `rotate` does
- [x] `cli.py` -- add `keys list [--inventory <path>] [--json]` subparser
- [x] `tests/conformance/test_keys_list.py` -- cover the I/O matrix
- [x] `tests/meta/test_invariants.py` -- `test_keys_list_output_never_contains_a_planted_secret_value`

**Acceptance Criteria:**
- Given `.steward/keys-inventory.yaml` after Stories 1.3/1.4 have created/rotated at least one identity, when `steward keys list` runs, then output includes that identity's name, scope, last-rotated timestamp, and `provenance: issued`.
- Given a second, `provenance: observed` entry (manually or auditor-populated), when `steward keys list` runs, then it is displayed alongside `issued` entries with its own provenance shown correctly.
- Given any flag combination (`--json`, default text), when `steward keys list` output is inspected, then it never contains a raw secret value — enforced by a dedicated `tests/meta/` test.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (adversarial re-read of the diff before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 1
- defer: 0
- reject: 0
- addressed_findings:
  - `[low]` `[patch]` The first draft's `format_inventory` JSON branch used `json.dumps(..., indent=2)` but the text branch's empty-inventory message ("no identities in the inventory") had no `--json` counterpart — `--json` against an empty inventory returned the string `"[]"` with no trailing newline while text mode's empty message read naturally; verified this is not actually a defect (an empty JSON array IS the correct, parseable `--json` empty-state answer — a human-readable sentence in `--json` mode would break every downstream parser) but added an explicit test (`test_keys_list_json_empty_inventory_is_an_empty_json_array`) pinning `[]` as the deliberate, tested contract rather than an implicit accident.
  - Verified by execution (not just inspection) that neither output path ever calls `.read_text()`/`.read_bytes()`/`open()` on `identity_path` or any `secrets` entry: `test_keys_list_output_never_contains_a_planted_secret_value` plants a real-looking secret string inside a file at the `identity_path` the test inventory points to, and asserts that string is absent from BOTH `list` output formats.

## Design Notes

**Why no `--scope`/`--status` filter flags:** neither is named by this story's AC, and Epic 1 has exactly one operator-facing consumer of `keys list` so far (a human reading the whole inventory) — filtering is speculative complexity ahead of a story that actually needs it (Simplicity First). Story 1.6's `keys audit --drift` is a distinct verb, not a filtered `list`.

**Why JSON carries `identity_path`/`secrets` but the text table doesn't:** the text table is for a human scanning at a glance (Story 1.5's literal AC fields: name/scope/provenance/status/last_rotated); JSON is for a script consuming the full record, where dropping fields would just force a second read of the YAML anyway. Both are read from the exact same `KeyIdentityEntry` tuple, so there is no risk of the two formats disagreeing on what's safe to show — they differ only in which already-vetted fields they choose to render, never in what they're allowed to touch.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: all tests pass (Stories 1.1-1.4's existing suite + this story's new tests)
- `pixi run -e pyforge-steward steward keys list --help` -- expected: shows `--inventory`/`--json`

**Results (2026-08-07):** all green — see the consolidated Verification note after Story 1.7.

</intent-contract>
