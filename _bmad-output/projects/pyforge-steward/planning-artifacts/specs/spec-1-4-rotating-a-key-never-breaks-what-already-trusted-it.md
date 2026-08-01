<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Story 1.4: Rotating a key never breaks what already trusted it'
type: 'feature'
created: '2026-07-30'
status: 'draft'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** Steward has no way to respond to a compromised (or just aging) `age` identity without the operator hand-decrypting and re-encrypting every affected secret and manually remembering which identity is now dead. There is also no on-disk credential inventory yet at all (Story 1.5 hasn't built `keys list`), so this story is the first to create and own `.steward/keys-inventory.yaml`'s shape.

**Approach:** Add `keys.py`'s `rotate_identity`, a thin orchestration over Story 1.3's `encrypt_file`/`decrypt_file` plus a new `age-keygen` subprocess wrap (AD-1/AD-3 — never vendored crypto). It looks up the scope's current `active`/`issued` inventory entry, generates a fresh identity, re-encrypts every secret path that entry lists (via a `tempfile`-staged decrypt-then-encrypt, never leaving plaintext in a durable location), then rewrites the inventory: the old entry flips to `status: retired`, a new entry (same `scope`, incremented generation name) becomes `active`. Wired as `steward keys rotate --scope <name> --new-identity <path>` via `KeysDuty`.

## Boundaries & Constraints

**Always:**
- `age-keygen` is invoked as a subprocess (AD-1/AD-3), never vendored — `age-keygen -o <new_identity_path>`, parsing the `Public key: ` line the same way the existing test helper does.
- The identity **secret-key file itself never lives inside a tracked path this story writes to** — `.steward/keys-inventory.yaml` stores only `identity_path` (a filesystem pointer, not the key material), `name`, `scope`, `provenance`, `status`, `last_rotated`, and the `secrets` paths it protects — never a secret value (mirrors the architecture's FR-5 provenance convention).
- `rotate_identity` only rotates an entry with `provenance: issued` AND `status: active` for the given `--scope`; anything else (no entry, `observed` provenance, already `retired`) is a `ValueError` → clean `DutyResult(ok=False, ...)`, never a crash.
- Re-encryption stages plaintext only inside a `tempfile.TemporaryDirectory()` (owner-only permissions), cleaned up in a `finally`, and rewrites each secret's `.age` file **in place** at its existing path.
- `-` is rejected for `--new-identity` (mirrors `_reject_stdio_sentinel`'s existing rationale — `age-keygen -o -` would silently discard the key to a captured-and-dropped stdout).
- `KeysDuty.run` catches `ValueError`/`subprocess.CalledProcessError` from `rotate_identity` as a duty-level failure (`EXIT_FAILED`), matching encrypt/decrypt's existing boundary (AD-8: never conflated with `EXIT_INTERNAL`).
- No calendar/cron/scheduler path anywhere in this story's code — rotation is on-demand only (PRD D1 / FR-3).

**Block If:** none — self-contained CLI + library work, no ambiguous external decision points.

**Never:**
- No `steward keys issue`/bootstrap CLI verb. Creating a scope's very FIRST inventory entry is out of this story's tested scope — this story's own tests construct that pre-existing entry directly (via `age-keygen` + `encrypt_file` + a hand-written inventory document), mirroring Story 1.3's identical precedent of generating test identities directly rather than through a Steward primitive. `rotate_identity` requires an entry to already exist; it does not create one from nothing.
- No deletion of the old identity's secret-key file — it is left on disk untouched (Steward doesn't own that path); "decrypting under the old identity now fails" falls out structurally once the `.age` ciphertext at each secret path has been rewritten to the new recipient.
- No `steward keys list`/`keys audit` verb, no `provenance: observed` write path — Stories 1.5/1.6.
- No revocation, no third-party provider API — Story 1.7.
- No full transactional rollback across a multi-secret rotation — inherits Story 1.3's existing known non-atomicity of a single `age --output` write (already on the deferred-work ledger); a rotation interrupted mid-list can leave some secrets re-encrypted and others not, with the inventory still showing the old entry active. Not solved this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy-path rotation | An `issued`/`active` entry for `scope`, 2 secrets encrypted to its identity | Both secrets decrypt under the new identity; old entry becomes `retired`; a new `active` entry appears for `scope` | No error expected |
| Old identity now fails | Same, post-rotation | `decrypt_file(secret, identity=old_identity_path, ...)` raises | `CalledProcessError` (age rejects: no matching recipient) |
| Unknown scope | No entry exists for `scope` | Inventory unchanged; nothing re-encrypted | `ValueError` at the primitive / `DutyResult(ok=False)` via CLI |
| Entry is `observed`, not `issued` | An entry exists but `provenance: observed` | Rotation refused | `ValueError` / `DutyResult(ok=False)` |
| `--new-identity -` | Any valid scope | Refused before touching any file | `ValueError` / `DutyResult(ok=False)` |
| No calendar trigger | This story's code + tests inspected | No scheduler/cron/time-based path found | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py` -- add `KeyIdentityEntry`, `InventoryError`, `load_inventory`/`save_inventory`, `rotate_identity`, and the `rotate` verb on `KeysDuty`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- add `keys rotate --scope --new-identity` subparser; extend `_KEYS_VERBS`/`_HELP["keys"]`
- `src/shared/packages/pyforge-steward/pixi.toml` -- add `pyyaml = "*"` to `[package.run-dependencies]` (mirrors `pyforge-warden`'s own unpinned convention for this same library — no NFR-C1-style version-evidence case exists for a generic data-format parser the way there was for `age`)
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_rotate.py` -- NEW: covers the I/O matrix, both at the primitive level and via `main(["keys", "rotate", ...])`
- `src/shared/packages/pyforge-steward/tests/conformance/test_keys_encrypt_decrypt.py` -- READ-ONLY reference: `_generate_identity` test helper's `age-keygen` invocation and pubkey-parsing pattern, reused for the new identity generated by rotation
- `src/shared/packages/pyforge-warden/src/pyforge/warden/waiver.py` -- READ-ONLY reference: `yaml.safe_load`/`yaml.safe_dump`-only convention, missing-file-is-empty precedent, typed `ValueError` subclass per failure mode

## Tasks & Acceptance

**Execution:**
- [ ] `pixi.toml` (package) -- add `pyyaml = "*"` to `[package.run-dependencies]` -- the inventory file's read/write format
- [ ] `keys.py` -- add `KeyIdentityEntry` (frozen dataclass: `name`, `scope`, `provenance`, `status`, `last_rotated`, `identity_path`, `secrets: tuple[str, ...]`) and `InventoryError(ValueError)`
- [ ] `keys.py` -- add `load_inventory(path) -> tuple[KeyIdentityEntry, ...]` / `save_inventory(path, entries)` -- `yaml.safe_load`/`yaml.safe_dump` only (never `yaml.load`/`unsafe_load`); missing file loads as `()`, mirrors `load_waivers`'s precedent
- [ ] `keys.py` -- add `rotate_identity(inventory_path, *, scope, new_identity_path)` -- finds the `issued`/`active` entry for `scope` (else `InventoryError`), generates the new identity via `age-keygen`, stages decrypt→encrypt per secret through a `TemporaryDirectory`, rewrites the inventory (old entry `retired`, new entry `active` with an incremented generation name), returns the new entry
- [ ] `keys.py` -- extend `KeysDuty`'s `_KEYS_VERBS`/`run` with `rotate`, catching `ValueError`/`CalledProcessError` the same way `encrypt`/`decrypt` already do
- [ ] `cli.py` -- add `keys rotate --scope <name> --new-identity <path>` subparser
- [ ] `tests/conformance/test_keys_rotate.py` -- cover every I/O matrix row, at both the primitive and CLI level

**Acceptance Criteria:**
- Given a pre-existing `.steward/keys-inventory.yaml` entry with `provenance: issued`/`status: active` and one or more secrets encrypted to its identity, when `steward keys rotate --scope <name> --new-identity <path>` runs, then every one of those secrets decrypts correctly under the identity newly generated at `<path>`, decrypting any of them under the old identity now fails, and the inventory shows the old entry `status: retired` with a new `status: active` entry for the same `scope`.
- Given this story's own code and test suite, when inspected, then no scheduler, cron entry, or time-based auto-rotation path exists anywhere — rotation is on-demand only (FR-3, PRD D1).
- Given `pixi run -e pyforge-steward pyforge-steward-test`, when the suite runs, then all of Stories 1.1-1.3's existing tests plus this story's new tests pass, and `steward --help`/`--version` are unchanged.

## Spec Change Log

## Review Triage Log

## Design Notes

**Why two inventory fields (`name` + `scope`), not one:** Story 1.5's own AC (epics.md) lists an identity's "name, scope, last-rotated timestamp" as three separate displayable fields — this story's schema takes that at face value rather than inventing a different shape Story 1.5 would have to reconcile. `scope` is the stable grouping key (the `--scope` CLI value, constant across a credential's whole rotation history); `name` is each individual identity-generation's own unique key (`<scope>` for the first, `<scope>-2`/`<scope>-3`/... for each rotation), so both the retired and the active record for one scope can coexist as independently inspectable entries — the literal reading of "the old identity is marked retired **in the inventory**" requires that a retired record actually exists there, not just that some in-place field flips with no trace of what it replaced.

**Why the identity file path is safe to store, but never its content:** an `age` identity is a private key — committing it to Git would defeat the entire premise of this epic. `identity_path` is only a filesystem pointer (the architecture's own Structural Seed keeps `.steward/` to `budget.yaml`/`keys-inventory.yaml`/`*.age` — no identity file listed), so the operator's actual key material stays wherever they put it, inside or outside the repo, un-tracked. This is also why `rotate_identity` takes `new_identity_path` as an explicit required argument rather than inventing a default location under `.steward/` — an implicit default would risk landing a private key inside the one directory this epic promises never holds one.

**Why re-encryption overwrites in place instead of a rename-swap:** `age`'s own `--output` write is not atomic (already a known, deferred limitation of `encrypt_file` from Story 1.3) — this story does not add a second, parallel atomicity mechanism on top of a primitive that itself has none; the existing ledger entry already tracks it for both primitives uniformly.

## Verification

**Commands:**
- `pixi install -e pyforge-steward` -- expected: resolves cleanly with `pyyaml` added
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: all tests pass (Stories 1.1-1.3's existing suite + this story's new tests)
- `pixi run -e pyforge-steward steward keys rotate --help` -- expected: shows `--scope`/`--new-identity`
</intent-contract>
