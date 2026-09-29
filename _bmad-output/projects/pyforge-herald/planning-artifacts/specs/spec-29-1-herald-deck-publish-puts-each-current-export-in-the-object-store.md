---
title: '29.1: herald deck publish puts each current export in the object store'
type: 'feature'
created: '2026-09-28'
status: 'blocked'
blocking_condition: 'blocked until steward Story 74.1 (the object-storage seam''s first-consumer contract: the configuration names, the bucket and prefix, the Helm values) has landed on main; the operator flips the ledger key, never a session'
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.herald.deck_publish
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # per-env values need feature-flag-governance:CAP-5 (steward); until then the tree default is off
  scope: global                                # v1 is global only (Q5)
  fallback: 'no deck is published; herald deck publish and herald deck exports stay listed as disabled and exit 2, and the exports live in git only, as today'
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-28-1-each-deck-keeps-one-current-version-of-each-export.md
  - src/platform/config/object_storage.py
  - src/platform/config/settings/base.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py
  - docs/governance/spec-feature-flag-governance/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Every current deck export lives only in git. The operator ruled on 2026-09-28 that
decks stay tracked and that each current export is *also* published to the platform's object
store with a metadata row, so that readers inside the enterprise airgap can be served from the
platform (Epic 30) and git stops being the only home. The object-storage seam
(`src/platform/config/object_storage.py`, `spec-pyforge-steward:CAP-94..97`) says "No existing
feature is wired to consume this seam yet". Bytes in PostgreSQL were rejected.

**Approach:** Two new herald modules and two verbs.
- `pyforge.herald.deck_store` is the only herald module that touches the store. It is a port
  (`put_if_absent(key, stream, content_type)`, `head(key)`, `open_stream(key)`) with an S3 adapter
  and an in-memory fake. The adapter is configured from the process environment only: the three
  settings the platform seam reads (`OBJECT_STORAGE_ENDPOINT_URL`, `OBJECT_STORAGE_ACCESS_KEY`,
  `OBJECT_STORAGE_SECRET_KEY`), plus the bucket and key prefix, under the contract steward Story
  74.1 lands. It never imports the host's `config.object_storage` (CAP-54 D2).
- `pyforge.herald.deck_publish` resolves each current export of a deck through
  `pyforge.herald.deck_versions` (Story 28.1, CAP-53's rule). It hashes each one with sha256 and
  streams it to `<prefix>/sha256/<hex>` when that key is absent. Then it writes the deck's
  manifest, `<prefix>/manifests/<slug>.json`, with one record per export: topic, kind, date, size,
  content type, sha256 and source commit (the HEAD sha that holds the tracked file) (D1).
- `herald deck publish <slug> [--dry-run]` runs it. `herald deck exports <slug> --json` reads the
  manifest back. Both are behind `pyforge.herald.deck_publish`.

Ledger key: `29-1-herald-deck-publish-puts-each-current-export-in-the-object-store`.
Ledger status (do not edit the ledger): `blocked`, until steward Story 74.1 lands; the operator flips it.
Type / Effort / Deps: feature / M / S-28.1.

### Living CAP citations

- `spec-pyforge-herald` CAP-54 (FR-10.1; decisions D1, D2 and the D3 precision in `.memlog.md`); AD-22; CAP-53 (the current-export rule).
- canopy:AD-18 (the station package is the writer), canopy:AD-19 (secret references), pap:AD-2 (`src/platform/` never imports `pyforge.*`).
- `feature-flag-governance:CAP-1` (the flag block), `feature-flag-governance:CAP-4` (the two-state test fixture, when it lands).

## Acceptance Criteria

- Given the flag ON and a local store When `herald deck publish <slug>` runs Then it exits 0 and each current export of the deck is at `<prefix>/sha256/<hex>` and reads back byte-identical
- Given a deck already published When `herald deck publish <slug>` runs again Then it uploads nothing and the manifest is unchanged
- Given a published deck When `herald deck exports <slug> --json` runs Then it prints one record per export with topic, kind, date, size, content type, sha256 and source commit
- Given a superseded export still in the tree When publish runs Then only the current version of its kind is published
- Given the flag OFF When `herald --help` and `herald deck publish <slug>` run Then both verbs are listed as disabled and the verb exits 2 with a "flag off" message, touching nothing
- Given the base herald package When the import-boundary test runs Then no module outside a Django extra imports `django` or the host's `config` modules

## Tasks

- [ ] Re-read steward Story 74.1's landed contract; if it differs from D2's reading, follow 74.1 and append the deviation to the Spec memlog
- [ ] `deck_store.py`: the port, the S3 adapter, the in-memory fake
- [ ] `deck_publish.py`: current-export resolution through `deck_versions`, sha256, `put_if_absent`, the manifest
- [ ] `cli.py`: the two verbs behind the flag, listed as disabled when OFF
- [ ] `src/platform/config/flags.json`: the key, `defaultVariant` off
- [ ] Tests, including the ON/OFF test and the import-boundary meta-test
- [ ] If the S3 client library is missing from the `pyforge-herald` or `pyforge-guild` env: hand-edit `pixi.toml`, `pixi lock`, regenerate `environment.yaml`, run `pyforge-station-tests`
- [ ] Spec-surface reconcile for every Spec the detector names, then one scoped stamp each

## Boundaries & Constraints

**Always:**
- **Blocked until steward Story 74.1 has landed; the operator flips it.** Marshal's `Deps:` parser is station-local, so the cross-station precondition is a ledger gate (AGENTS.md § Known pitfalls). Do not start this story while 74.1 is unlanded.
- Publish only the current export of each kind (CAP-53 D2, through `pyforge.herald.deck_versions`); never a second definition of current.
- Stream: never read a whole export into memory. Hash while streaming or in bounded chunks.
- Credentials come from the environment only and are never printed, logged or accepted as CLI flags.
- Read every verdict from the exit code, never through a pipe.
- The PR carries the `maintenance` label.

**Never:**
- Do not write bytes or metadata to PostgreSQL; the manifest in the store is the metadata of record (D1).
- Do not import `config.object_storage`, `django` or any `src/platform/` module from the base herald package, and do not add a `pyforge.*` import under `src/platform/`.
- Do not edit steward-owned files (the chart's values, the seam contract, `src/platform/config/object_storage.py`).
- Do not untrack or delete a deck export; AD-4 and CAP-53 are unchanged.
- Do not flip this story's ledger key, or any other `blocked` key.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| first publish | a deck with 4 current exports, empty store | 4 objects under `sha256/`, a manifest with 4 records | exit 0 |
| second publish | nothing changed | zero uploads, manifest byte-identical | exit 0 |
| one export changed | a newer dated export replaced the old one (28.2) | one new object; the manifest record for that kind points at it | exit 0 |
| superseded file present | two versions of one kind in the tree | only the newest is published | exit 0 |
| store unset | no endpoint in the environment | named refusal naming the missing setting, nothing written | exit 1 |
| store unreachable | endpoint refuses | named error, manifest not rewritten | exit 1 |
| `--dry-run` | any | prints what would upload, writes nothing | exit 0 |
| flag OFF | any | verbs listed as disabled; "flag off" | exit 2 |
| unknown slug | `herald deck publish nosuch` | usage error | exit 2 |
| 74.1 absent | dispatched before 74.1 landed | refused: the ledger key is `blocked` | operator gate |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald` CAP-54 (FR-10.1; D1, D2).
Architecture: AD-22.
Dream: `docs/dreams/pyforge-herald.md` § Realization log → *2026-09-28 (night) — Proposed: a deck can be read inside the airgap, from the portal and from an internal Pages site, and each current export is also kept in object storage*.
Ledger key: `29-1-herald-deck-publish-puts-each-current-export-in-the-object-store`.
Ledger status at mint: `blocked`, until steward Story 74.1 has landed; the operator flips it.
Deps: S-28.1 (the `deck_versions` rule). Cross-station gate: steward Story 74.1.
Flag: `pyforge.herald.deck_publish` (`feature-flag-governance:CAP-1`).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-28.1 • **FR/AD:** spec-pyforge-herald CAP-54 (FR-10.1; D1, D2); AD-22 • cross-project gate: steward Story 74.1 must have landed first — the ledger key is minted `blocked` and the operator flips it • flag: `pyforge.herald.deck_publish`

**Given** each current export lives only in git, and the platform's object-storage seam has no consumer
**When** `herald deck publish <slug>` runs with the flag ON against a local store (the `platform-object-storage` silo server)
**Then** it exits 0; each current export sits at `<prefix>/sha256/<hex>` and reads back byte-identical; the manifest carries topic, kind, date, size, content type, sha256 and source commit for each; a second run uploads nothing; `herald deck exports <slug> --json` prints the records
**And** with the flag OFF both verbs are listed as disabled and exit 2 with a "flag off" message; the boundary test finds no `django` or `config` import in the base package; `pyforge-herald-test` is green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; the store fake, the publish cases, the ON/OFF test and the import-boundary meta-test run inside it).

**Manual checks:**
- ON/OFF: the flag test writes two flagd trees (one with `pyforge.herald.deck_publish` ON, one OFF), like `src/platform/tests/test_openfeature_file_flags.py`, points `PYFORGE_FLAGS_PATH` at each, and asserts publish succeeds ON and exits 2, listed as disabled, OFF. Replace it with the testing-kit fixture once `feature-flag-governance:CAP-4` lands.
- Live against the local store: `pixi run -e platform-object-storage platform-object-storage-up`, then `herald deck publish pyforge-herald` twice; the second run reports zero uploads.
- If `pixi.toml` changed: `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass; `environment.yaml` regenerated in the same PR.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the reconcile and the scoped stamps.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code.

## Review Triage Log
