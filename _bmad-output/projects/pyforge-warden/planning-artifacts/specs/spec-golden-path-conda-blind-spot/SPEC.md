---
spec: golden-path-conda-blind-spot
status: draft
owner-dream: docs/dreams/golden-path-conda-blind-spot.md
surface: []
companions:
  - brownfield.md
  - ../../osv-db-offline-provisioning-decision.md
  - ../spec-2-1-conda-pypi-map-the-ecosystem-identity-predicate.md
sources:
  - ../../../../../../docs/dreams/golden-path-conda-blind-spot.md
open_questions:
  - "Selector grammar: extractor constructor args plus which CLI flags (--pixi-environment / --pixi-platform?); does the platform default to the host or must CI pass it explicitly?"
  - "Provisioning: which decision-record route does CI take, where is the DB cached across runs (actions/cache keyed by snapshot date?), and who owns its refresh cadence?"
  - "Coverage floor: does promotion also require 100 % assessed coverage (--fail-under-coverage) or is a clean rung alone the gate?"
  - "Is a warn verdict ever promotable with a recorded Story 3.2 waiver, or is clean the only promotable rung?"
  - "Should the unscoped union extraction stay the default for other callers, or become an explicit error on a multi-environment lockfile?"
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. The Dream in `sources:` is traceability only.

# SPEC — A promotion gate that has never seen what it ships

## Why
A pain, and a gate that is now fail-closed. `golden-path-promotion` (steward
Story 43.4) ran for the first time on 2026-09-04 and recorded a Warden verdict
of `indeterminate` over 329 components, 0 assessed for vulnerabilities — and it
can never say anything else: it scans a bare `pixi.toml` staged in a scratch dir
because `PixiLockExtractor` flattens every environment and platform the
workspace `pixi.lock` ever resolved (28 environments; the image ships one), a
bare manifest carries no locked versions so identity degrades to `NO_VERSION`
before OSV can match, and no CI job provisions the offline OSV database, so the
absent-DB rule from Story 1.4 correctly routes to `indeterminate`. Since
`1016f4e763` (2026-09-04) `platform-deploy` refuses any verdict that is not
`clean`, so today nothing promotes until the verdict is real.

## Capabilities
- **CAP-1 — environment-scoped lockfile extraction.**
  - **intent:** Warden extracts exactly the packages one named pixi environment
    resolves for one platform from a multi-environment `pixi.lock`, instead of
    the union of everything the file ever resolved.
  - **success:** scanning this repo's root `pixi.lock` scoped to
    `python-agent-platform` / `linux-64` yields the same set as that
    environment's `packages.linux-64` list in the lock (count, names,
    versions), with no other environment's exclusive packages; the unscoped
    call keeps today's union behaviour.
- **CAP-2 — the promotion scans the shipped closure.**
  - **intent:** `golden-path-promotion` scans the resolved
    `python-agent-platform` environment out of the root `pixi.lock` — the
    thing built into the image — not a bare `pixi.toml` in a scratch dir.
  - **success:** the promotion record's components equal the CAP-1 set, every
    component carries a locked version (no `NO_VERSION` from an unresolved
    manifest), and the scratch-dir staging is gone.
- **CAP-3 — the offline OSV database is provisioned in CI.**
  - **intent:** the promotion job runs with a real, provenance-bearing offline
    OSV database, provisioned by the mechanism the Story 1.4 decision record
    already accepted, so the vulnerability axis assesses every
    identity-resolved component.
  - **success:** `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` points at a populated
    `<cache>/osv-scanner/PyPI/all.zip` with a recorded `snapshot_at`; the
    record's vulnerability axis reports assessed > 0; a DB older than
    `db-max-age` (7 days, strict) or without provenance routes the verdict to
    `indeterminate`, never `clean`.
- **CAP-4 — the verdict is honest and specific.**
  - **intent:** `warden_status` is `clean` only when the shipped closure's
    conda+pypi identity is scanned end to end; anything short of that is
    `indeterminate` / `warn` with a nameable gap, never a permanent
    architectural `indeterminate`.
  - **success:** on a not-clean verdict the record names the unassessed
    components and the reason (`UNMAPPED_ECOSYSTEM`, stale DB, missing DB); a
    deliberately pinned vulnerable version in the environment flips the record
    to a failing rung that names the finding.
- **CAP-5 — deploy gates on the verdict (already true on main — preserve).**
  - **intent:** `platform-deploy` promotes a digest only when its recorded
    verdict is `clean` (shipped in `1016f4e763`; this spec keeps it).
  - **success:** the verifier refuses `indeterminate` / `warn` / `fail` and a
    missing record, accepts `clean`, names the driver finding id, and a test
    fails if the `!= 'clean'` refusal is removed.

## Constraints
- Never promote to `clean` by loosening what counts as scanned: a selector that
  cannot resolve a component's identity keeps withholding it
  (`UNMAPPED_ECOSYSTEM`); it never drops it from the denominator.
- Reuse the two accepted designs — spec-2-1's verified-confidence conda→pypi
  map and the Story 1.4 decision record (mechanism, 7-day strict staleness,
  unknown or future-dated provenance ⇒ `indeterminate`, trust anchor). Do not
  re-derive matching or staleness semantics.
- Offline-first (NFR-S2): provisioning the database is an explicit, non-default
  CI step; the scan itself never egresses silently.
- The two halves stay together: the verifier's clean-only gate is never relaxed
  to make deploy pass; the real verdict lands under it.
- Scope is `pyforge-warden/extract/lockfiles.py`,
  `scripts/platform-golden-path-promotion.sh` and the `golden-path-promotion`
  job in `platform-ci.yml`.

## Non-goals
- A general multi-environment / multi-platform selector for every future Warden
  caller — one named environment, the current platform; widen only when a
  second caller needs it.
- A new conda-native vulnerability data source — OSV via the conda→pypi
  identity is v1; revisit only if it proves insufficient.
- The CFE atlas's own `pixi.lock` parser (`scan_project`) — a separate, working
  subsystem.
- Relaxing the deploy verifier.

## Success signal
The first `golden-path-promotion` run after this lands records
`warden_status: clean` over the `python-agent-platform` closure with every
component's vulnerability axis assessed, and `platform-deploy` promotes that
digest; a deliberately planted vulnerable pin in the same environment flips the
next record to a failing rung that `platform-deploy` refuses.

## Assumptions
- Target is `python-agent-platform` on `linux-64` (the platform Containerfile
  pins `--platform=linux/amd64`); no other environment is in scope.
- Warden's existing seven-rung lattice supplies every not-clean rung; no new
  rung or verdict field.
- Provisioning defaults to osv-native `--download-offline-databases` on the
  connected CI runner with snapshot provenance recorded, unless a
  conda-packaged DB exists by story time (the decision record's §1 order).
- The environment/platform selector is an extractor option surfaced through
  the warden CLI; exact flag names are a story-time decision.

## Open Questions
- Selector grammar: extractor constructor args plus which CLI flags
  (`--pixi-environment` / `--pixi-platform`?); does the platform default to
  the host or must CI pass it explicitly?
- Provisioning: which decision-record route does CI take, where is the DB
  cached across runs (actions/cache keyed by snapshot date?), and who owns its
  refresh cadence?
- Coverage floor: does promotion also require 100 % assessed coverage
  (`--fail-under-coverage`) or is a `clean` rung alone the gate?
- Is a `warn` verdict ever promotable with a recorded Story 3.2 waiver, or is
  `clean` the only promotable rung?
- Should the unscoped union extraction stay the default for other callers, or
  become an explicit error on a multi-environment lockfile?
