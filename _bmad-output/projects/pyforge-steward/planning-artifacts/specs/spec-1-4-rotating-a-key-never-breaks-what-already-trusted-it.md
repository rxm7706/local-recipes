<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-07 -->
---
title: 'Story 1.4: Rotating a key never breaks what already trusted it'
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

**Problem:** Steward has no way to respond to a compromised (or just aging) `age` identity without the operator hand-decrypting and re-encrypting every affected secret and manually remembering which identity is now dead. There is also no on-disk credential inventory yet at all (Story 1.5 hasn't built `keys list`), so this story is the first to create and own `.steward/keys-inventory.yaml`'s shape.

**Approach:** Add `keys.py`'s `rotate_identity`, a thin orchestration over Story 1.3's `encrypt_file`/`decrypt_file` plus a new `generate_identity` (`age-keygen`) subprocess wrap (AD-1/AD-3 — never vendored crypto). It looks up the scope's current `issued`/`active` inventory entry, generates a fresh identity, re-encrypts every secret path that entry lists (via a `tempfile`-staged decrypt-then-encrypt, never leaving plaintext in a durable location), then rewrites the inventory: the old entry flips to `status: retired`, and a new entry (same `scope`, incremented generation name) becomes `active`. Wired as `steward keys rotate --scope <name> --new-identity <path> [--inventory <path>]` via `KeysDuty`.

## Boundaries & Constraints

**Always:**
- `age-keygen` is invoked as a subprocess (AD-1/AD-3), never vendored — `age-keygen -o <new_identity_path>`, parsing the `Public key: ` line the same way Story 1.3's own test helper does.
- The identity **secret-key file itself never lives inside a tracked path this story writes to** — `.steward/keys-inventory.yaml` stores only `identity_path` (a filesystem pointer, not key material), plus `name`, `scope`, `provenance`, `status`, `last_rotated`, `secrets` — never a secret value (architecture's FR-5 provenance convention, ARCHITECTURE-SPINE.md's Consistency Conventions table).
- `rotate_identity` only rotates an entry with `provenance == "issued"` AND `status == "active"` for the given `scope`; anything else (no entry, `observed` provenance, already `retired`) raises `InventoryError` (a `ValueError` subclass) → a clean `DutyResult(ok=False, ...)` via the CLI, never a crash.
- Re-encryption stages plaintext only inside a `tempfile.TemporaryDirectory()`, cleaned up automatically on context exit (including on error — `TemporaryDirectory` is itself the cleanup guarantee), and rewrites each secret's `.age` file **in place** at its existing path.
- `-` is rejected for `--new-identity` (mirrors `_reject_stdio_sentinel`'s existing rationale — `age-keygen -o -` would silently discard the key to a captured-and-dropped stdout). The existing two-role `_reject_stdio_sentinel` is generalized into a reusable single-role `_reject_dash(role, value)` so this story's one-path check doesn't duplicate the message.
- Rotation only ever references the old identity by its `identity_path` pointer — rotation never reads or logs the identity's secret-key file contents; the only value derived from `age-keygen`'s output that is ever printed or stored is the new identity's *public* key (not a secret) or its file path.
- `KeysDuty.run` catches `ValueError` (covers `InventoryError`) and `subprocess.CalledProcessError` from `rotate_identity` as a duty-level failure (`EXIT_FAILED`), matching encrypt/decrypt's existing boundary (AD-8: never conflated with `EXIT_INTERNAL`).
- No calendar/cron/scheduler path anywhere in this story's code — rotation is on-demand only (PRD D1 / FR-3). A dedicated meta test scans `keys.py`'s source text for scheduler-shaped tokens (`cron`, `schedule`, `apscheduler`, `celery`) to pin this as a regression-tested invariant, not just a code-review claim.

**Block If:** none — self-contained CLI + library work, no ambiguous external decision points.

**Never:**
- No `steward keys issue`/bootstrap CLI verb. Creating a scope's very FIRST inventory entry is out of this story's tested scope — this story's own tests construct that pre-existing entry directly (via `age-keygen` + `encrypt_file` + `save_inventory`), mirroring Story 1.3's identical precedent of generating test identities directly rather than through a Steward primitive. `rotate_identity` requires an entry to already exist; it does not create one from nothing.
- No deletion of the old identity's secret-key file — it is left on disk untouched (Steward doesn't own that path); "decrypting under the old identity now fails" falls out structurally once the `.age` ciphertext at each secret path has been rewritten to the new recipient.
- No `steward keys list`/`keys audit` verb, no `provenance: observed` write path — Stories 1.5/1.6.
- No revocation, no third-party provider API — Story 1.7.
- No full transactional rollback across a multi-secret rotation — inherits Story 1.3's existing known non-atomicity of a single `age --output` write (already on the deferred-work ledger); a rotation interrupted mid-list can leave some secrets re-encrypted and others not, with the inventory still showing the old entry active. Not solved this story (recorded in Deferred Work below).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy-path rotation | An `issued`/`active` entry for `scope`, 2 secrets encrypted to its identity | Both secrets decrypt under the new identity; old entry becomes `retired`; a new `active` entry appears for `scope` with the same secret paths | No error expected |
| Old identity now fails | Same, post-rotation | `decrypt_file(secret, identity=old_identity_path, ...)` raises | `CalledProcessError` (age rejects: no matching recipient) |
| Unknown scope | No entry exists for `scope` | Inventory unchanged; nothing re-encrypted; no `age-keygen` invoked | `InventoryError` (`ValueError`) at the primitive / `DutyResult(ok=False)` via CLI |
| Entry is `observed`, not `issued` | An entry exists but `provenance: observed` | Rotation refused | `InventoryError` / `DutyResult(ok=False)` |
| Entry is already `retired` | An entry exists but `status: retired` (no other active entry for `scope`) | Rotation refused | `InventoryError` / `DutyResult(ok=False)` |
| `--new-identity -` | Any valid scope | Refused before touching any file or the inventory | `ValueError` / `DutyResult(ok=False)` |
| No calendar trigger | This story's code inspected | No scheduler/cron/time-based path found | Meta test, not a runtime path |
| Rotate twice | An `active` entry, rotate, then rotate the resulting new `active` entry again | Second rotation produces a THIRD inventory entry (`<scope>-3`); the second entry also flips to `retired` | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` -- generalize `_reject_stdio_sentinel` into `_reject_dash`; add `generate_identity`, `repo_root`, `default_inventory_path`, `KeyIdentityEntry`, `InventoryError`, `load_inventory`/`save_inventory`, `rotate_identity`, and the `rotate` verb on `KeysDuty`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- add `keys rotate --scope --new-identity [--inventory]` subparser; extend `_KEYS_VERBS`/`_HELP["keys"]`
- `src/shared/packages/pyforge-steward/pixi.toml` -- add `pyyaml = "*"` to `[package.run-dependencies]` (mirrors `pyforge-warden`'s own unpinned convention for this same library — no NFR-C1-style version-evidence case exists for a generic data-format parser the way there was for `age`)
- `src/shared/packages/pyforge-steward/pyproject.toml` -- add `"PyYAML"` to `[project].dependencies` (mirrors `pyforge-warden`'s pyproject listing the same library it also declares as a pixi run-dependency)
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_rotate.py` -- NEW: covers the I/O matrix, both at the primitive level and via `main(["keys", "rotate", ...])`
- `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` -- add `test_no_rotation_scheduler_exists` (AC's no-cron/scheduler claim, made a regression test)
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_encrypt_decrypt.py` -- READ-ONLY reference: `_generate_identity` test helper's `age-keygen` invocation and pubkey-parsing pattern, reused (as `generate_identity`, promoted to a real primitive) for the new identity generated by rotation
- `src/shared/packages/pyforge-warden/src/pyforge/warden/waiver.py` -- READ-ONLY reference: `yaml.safe_load`/`yaml.safe_dump`-only convention, missing-file-is-empty precedent, typed `ValueError` subclass per failure mode

## Tasks & Acceptance

**Execution:**
- [x] `pixi.toml` (package) -- add `pyyaml = "*"` to `[package.run-dependencies]` -- the inventory file's read/write format
- [x] `pyproject.toml` -- add `"PyYAML"` to `dependencies` -- mirrors warden's own dual declaration
- [x] `keys.py` -- generalize `_reject_stdio_sentinel` into `_reject_dash(role, value)`, keeping the two-role wrapper for `encrypt_file`/`decrypt_file`'s existing call sites unchanged
- [x] `keys.py` -- add `generate_identity(output_path) -> str` -- `age-keygen -o` subprocess wrap, returns the parsed public key; raises `ValueError` for `-`, propagates `CalledProcessError`
- [x] `keys.py` -- add `repo_root()` / `default_inventory_path()` -- repo-root-relative `.steward/keys-inventory.yaml` (Consistency Conventions), resolved by walking up from this module the same way `locate_http_module` does
- [x] `keys.py` -- add `KeyIdentityEntry` (frozen dataclass: `name`, `scope`, `provenance`, `status`, `last_rotated`, `identity_path`, `secrets: tuple[str, ...]`) and `InventoryError(ValueError)`
- [x] `keys.py` -- add `load_inventory(path) -> tuple[KeyIdentityEntry, ...]` / `save_inventory(path, entries)` -- `yaml.safe_load`/`yaml.safe_dump` only (never `yaml.load`/`unsafe_load`); missing file loads as `()`, mirrors `load_waivers`'s precedent; malformed shape raises `InventoryError`
- [x] `keys.py` -- add `rotate_identity(inventory_path, *, scope, new_identity_path)` -- finds the `issued`/`active` entry for `scope` (else `InventoryError`), generates the new identity, stages decrypt→encrypt per secret through a `TemporaryDirectory`, rewrites the inventory (old entry `retired`, new entry `active` with an incremented generation name), returns the new entry
- [x] `keys.py` -- extend `KeysDuty`'s `_KEYS_VERBS`/`run` with `rotate`, catching `ValueError`/`CalledProcessError` the same way `encrypt`/`decrypt` already do; success summary names the scope and new entry name/path, never the public key or identity contents
- [x] `cli.py` -- add `keys rotate --scope <name> --new-identity <path> [--inventory <path>]` subparser
- [x] `tests/conformance/test_keys_rotate.py` -- cover every I/O matrix row, at both the primitive and CLI level
- [x] `tests/meta/test_invariants.py` -- `test_no_rotation_scheduler_exists`

**Acceptance Criteria:**
- Given a pre-existing `.steward/keys-inventory.yaml` entry with `provenance: issued`/`status: active` and one or more secrets encrypted to its identity, when `steward keys rotate --scope <name> --new-identity <path>` runs, then every one of those secrets decrypts correctly under the identity newly generated at `<path>`, decrypting any of them under the old identity now fails, and the inventory shows the old entry `status: retired` with a new `status: active` entry for the same `scope`.
- Given this story's own code and test suite, when inspected, then no scheduler, cron entry, or time-based auto-rotation path exists anywhere — rotation is on-demand only (FR-3, PRD D1).
- Given `pixi run -e pyforge-steward pyforge-steward-test`, when the suite runs, then all of Stories 1.1-1.3's existing tests plus this story's new tests pass, and `steward --help`/`--version` are unchanged.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review pass (adversarial re-read of the diff before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 1
- defer: 1
- reject: 0
- addressed_findings:
  - `[low]` `[patch]` The first draft's `rotate` success summary interpolated `entry.identity_path` (a filesystem pointer, not a secret) directly into `DutyResult.summary` with no explicit test asserting the *public key* is never also included — added `test_rotate_summary_never_contains_the_public_key`, asserting the pubkey `generate_identity` returns never appears in `DutyResult.summary`. Closes the same class of "never a secret value" gap Story 1.5 tests for `keys list` output, one story early since `rotate` is the first verb that ever handles a public key.
  - `[low]` `[defer]` `rotate_identity` has no protection against being invoked twice concurrently on the same inventory file (a read-modify-write race: two processes could each read the same `active` entry, each generate a new identity, and each rewrite the inventory, with the second `save_inventory` silently clobbering the first's new entry). Deferred: Steward is an interactively-invoked local CLI with no daemon/concurrent-caller model anywhere else in this epic; file locking here would be complexity ahead of any story that actually calls for concurrent invocation. Recorded in `deferred-work.md`.
  - Verified structurally (not just by inspection) that a mid-rotation `age`/`age-keygen` failure cannot produce the title's forbidden outcome — a secret simultaneously invalid under BOTH the old and new identity: `encrypt_file`'s `subprocess.run(check=True)` raises on any non-zero `age` exit, and a failing `age --encrypt` process does not write a truncated `--output` file in the normal failure path (confirmed empirically: an invalid-recipient run leaves no output file at all) — so a secret is always either still the OLD ciphertext (old identity still decrypts it) or the fully-written NEW ciphertext (new identity decrypts it), never a partial/corrupt write that satisfies neither. This traces back to Story 1.3's already-accepted `age --output` non-atomicity deferral, not a new gap.

## Design Notes

**Why two inventory fields (`name` + `scope`), not one:** Story 1.5's own AC (epics.md) lists an identity's "name, scope, last-rotated timestamp" as three separate displayable fields — this story's schema takes that at face value rather than inventing a different shape Story 1.5 would have to reconcile. `scope` is the stable grouping key (the `--scope` CLI value, constant across a credential's whole rotation history); `name` is each individual identity-generation's own unique key (`<scope>` for the first, `<scope>-2`/`<scope>-3`/... for each rotation), so both the retired and the active record for one scope can coexist as independently inspectable entries — the literal reading of "the old identity is marked retired **in the inventory**" requires that a retired record actually exists there, not just that some in-place field flips with no trace of what it replaced.

**Why the identity file path is safe to store, but never its content:** an `age` identity is a private key — committing it to Git would defeat the entire premise of this epic. `identity_path` is only a filesystem pointer (the architecture's own Structural Seed keeps `.steward/` to `budget.yaml`/`keys-inventory.yaml`/`*.age` — no identity file listed), so the operator's actual key material stays wherever they put it, inside or outside the repo, un-tracked. This is also why `rotate_identity` takes `new_identity_path` as an explicit required argument rather than inventing a default location under `.steward/` — an implicit default would risk landing a private key inside the one directory this epic promises never holds one.

**Why re-encryption overwrites in place instead of a rename-swap:** `age`'s own `--output` write is not atomic (already a known, deferred limitation of `encrypt_file` from Story 1.3) — this story does not add a second, parallel atomicity mechanism on top of a primitive that itself has none; the existing ledger entry already tracks it for both primitives uniformly.

**Inventory document shape (a judgment call this spec settles):** `{"identities": [...]}`, a top-level mapping rather than a bare list, so the schema has a stable place to grow a sibling key later (e.g. a schema-version marker) without a breaking shape change — no such key is added yet since nothing in Epic 1 needs it.

**Generation-name collision safety:** `generation = len(entries for this scope) + 1` (not parsing/incrementing the previous entry's numeric suffix) — monotonic and collision-free even if a future story deletes/edits entries out of band, since it always counts what's actually present rather than trusting a name it must then re-parse.

## Verification

**Commands:**
- `pixi install -e pyforge-steward` -- expected: resolves cleanly with `pyyaml` added
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: all tests pass (Stories 1.1-1.3's existing suite + this story's new tests)
- `pixi run -e pyforge-steward steward keys rotate --help` -- expected: shows `--scope`/`--new-identity`/`--inventory`

**Results (2026-08-07):** see this session's consolidated Verification note after Story 1.7 for the final combined pytest count; this story's own new tests were independently green at the point they were added, and re-verified green again after Stories 1.5-1.7 landed on top.

</intent-contract>
