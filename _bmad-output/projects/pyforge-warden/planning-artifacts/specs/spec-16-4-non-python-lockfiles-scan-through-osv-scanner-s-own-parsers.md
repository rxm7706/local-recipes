---
title: "16.4: Non-Python lockfiles scan through osv-scanner's own parsers"
type: 'feature'
created: '2026-09-28'
status: 'in-review'
baseline_revision: 'dcbddeb4e3fc40552d620e30782c89d9d30a9afa'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/extraction-contract.md
  - docs/dreams/pyforge-warden.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/discovery.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/vuln.py
flag:
  key: pyforge.warden.non_python_ecosystems
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "non-Python lockfiles are not discovered; the scan stays Python-only, as today"
  cleanup: 90 days after ON in every environment (Q4)
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Warden discovers and extracts Python manifests only (PyPI and conda-forge); the Spec listed "Non-Python
osv-scanner ecosystems (npm, Go, Rust, …)" as a Non-goal. The operator ruled on 2026-09-28 that Warden scans the
enterprise fleet, lifting that Non-goal for the security axis: most fleet repos are not Python, and a fleet run that
reports them all `not-applicable` would say nothing true about them. osv-scanner already parses those lockfiles natively.

**Approach:** Behind the flag, discovery recognizes the lockfiles osv-scanner parses natively (`package-lock.json`,
`yarn.lock`, `pnpm-lock.yaml`, `go.sum`, `Cargo.lock`, `Gemfile.lock`, `composer.lock` and the rest of its documented
list) and routes each to osv-scanner's own parser by path (`-L <parser>:<path>`), the way PyPI inputs are already
delegated (CAP-2) — `extract/` gains no parser and imports no execution primitive. The resulting components carry their
native ecosystem identity and a concrete version, so `vuln_matchable` holds on that identity (no conda↔PyPI mapping is
involved). The security axis assesses them; hygiene, license and currency report them honestly `not-applicable`, with
per-axis denominators that say so. The SBOM carries source-registry-correct purls (`pkg:npm/…`, `pkg:golang/…`,
`pkg:cargo/…`). The offline database must hold the ecosystem: a missing or stale one routes to `indeterminate`, never
`clean`. Container and artifact scanning stay out of scope.

Ledger key: `16-4-non-python-lockfiles-scan-through-osv-scanner-s-own-parsers`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-warden` CAP-26 (FR-43), the lifted Non-goal; CAP-2 (delegate to the engines' native parsers); CAP-3
  (assessed versus present); CAP-11 (offline database, staleness to `indeterminate`).
- `spec-feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given a fixture repo whose `package-lock.json` pins a known-vulnerable npm version and a fixture offline database holding that advisory, When `warden scan` runs with the flag ON, Then the report carries a `vuln:` finding for it and the security axis counts it as assessed
- Given the same component, When the other axes report, Then hygiene, license and currency count it `not-applicable`, and their denominators say so
- Given the SBOM, When it is emitted, Then the component's purl is `pkg:npm/<name>@<version>`
- Given no database for the ecosystem, or a stale one, When the scan runs, Then the verdict is `indeterminate` naming the ecosystem, never `clean`
- Given the flag OFF, When the same repo is scanned, Then the report is byte-identical to today's (the lockfile is not discovered)
- Given the extractor, When the AST-denylist meta-test runs, Then it stays green, and the report validates against `report-schema.json` 1.1.0

## Boundaries & Constraints

**Always:**
- Delegate parsing to osv-scanner; keep `extract/` a no-execution zone.
- Keep the `ComplianceReport` at 1.1.0 and the exit enum and lattice frozen.
- Keep per-ecosystem attribution; never merge an npm name with a PyPI or conda name.
- Read the flag only through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract) over the one tree (canopy:AD-11). If 75.1 has not landed when this story runs, add it in `pyforge.core` in exactly 75.1's shape (`read_boolean(key, default=False)`, `cutover_root.py`'s tree resolution, False with a named WARN for a missing tree, key or non-bool value; a `spec-pyforge-core` co-governor reconcile) — never a station-local reader or a second tree. Add the key to `src/platform/config/flags.json` (default OFF).
- Reconcile `spec-pyforge-warden` (and, for `extract/`, `spec-pyforge-core`, which co-governs `extract/__init__.py` and `extract/lockfiles.py`) and every Spec `spec-surface-check` names; scoped stamps only.

**Never:**
- Add hygiene (deptry), license or currency producers for non-Python ecosystems here.
- Scan containers, images or artifacts.
- Fetch a database at scan time; provisioning stays explicit (CAP-11, CAP-20).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| vulnerable npm lock | `package-lock.json` + DB | `vuln:` finding, security assessed | — |
| clean Go module | `go.sum`, no advisory | security assessed, no finding | — |
| no ecosystem DB | npm lock, PyPI-only DB | `indeterminate` naming npm | never `clean` |
| mixed repo | `pixi.toml` + `package-lock.json` | both scanned, attributed per ecosystem | — |
| flag OFF | any | today's report | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-warden` CAP-26 (FR-43) — the lifted *Non-Python osv-scanner ecosystems* Non-goal.
Dream: `docs/dreams/pyforge-warden.md` § Realization log → *2026-09-28 (night) — Proposed: the fix-PR actuator finishes the fix, SAST joins as a plugin, and Warden scans the enterprise fleet*.
Ledger key: `16-4-non-python-lockfiles-scan-through-osv-scanner-s-own-parsers`.
Ledger status at mint: `backlog`.
Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- Flag ON/OFF: a test writes two flagd trees (`pyforge.warden.non_python_ecosystems` on, then off; the `src/platform/tests/test_openfeature_file_flags.py` shape until the `spec-feature-flag-governance:CAP-4` fixture lands): ON scans the npm lock, OFF leaves the report byte-identical to today's.
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Review Triage Log

- No review yet (minted 2026-09-28). Implementation and review stay separate.
