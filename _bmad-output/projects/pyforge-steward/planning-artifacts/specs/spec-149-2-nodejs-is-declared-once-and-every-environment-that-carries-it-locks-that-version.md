---
title: '149.2: nodejs is declared once, and every environment that carries it locks that version'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 149-2-nodejs-is-declared-once-and-every-environment-that-carries-it-locks-that-version
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'pixi.toml'
  - 'pixi.lock'
  - 'environment.yaml'
  - 'docs/governance/pin-policy.yaml'
  - 'docs/reference/library-llms-full.md'
  - 'docs-site/.nvmrc'
  - 'docs-site/package.json'
  - 'docs-site/package-lock.json'
  - 'docs-site/README.md'
  - '.github/workflows/pyforge-station-tests.yml'
  - 'scripts/target_version_check.py'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_target_version_check_surfaces.py'
  - 'src/shared/packages/pyforge-herald/tests/meta/test_docs_site.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The platform ran three nodejs versions. Four features (`python`, `pyforge-steward`, `site`, `pyforge-herald`) declared the range `>=24.19.0,<27.0,!=25.*`. Six environments (`pyforge-atlas`, `detectors`, `bmad-ui`, `bmad-suite-full`, `mcp-host`, `platform-ci-test`) carried nodejs only because a package pulled it in. The lock held 24.21.0 (17 environment-platform pairs), 26.10.0 (36) and 26.13.1 (5). CI's atlas job set Node 22 up with `actions/setup-node`, and `docs-site/.nvmrc` and `engines` named 24 and `>=24`.

**Approach:** One table declares nodejs, `[feature.node.dependencies] nodejs = "24.22.3.*"`: the newest 24.x LTS release, inside the operator's range. A 26.13.1 declaration did not solve, because marp-cli 4.2.3 requires `nodejs >=24.4.1,<25`. Every environment that carries nodejs (24 of them) lists the `node` feature after `interpreter`, and no other feature names nodejs. `.nvmrc`, `engines` (with `package-lock.json`'s root entry) and the pin policy name 24.22.3. The atlas job's WASM build uses pyforge-atlas's own npm, so its `setup-node` step goes. `target-version-check` holds all of it.

Ledger key: `149-2-nodejs-is-declared-once-and-every-environment-that-carries-it-locks-that-version`.

### Living CAP citations

- spec-pyforge-steward CAP-153 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- nodejs stays inside the operator's range, `>=24.19.0,<27.0,!=25.*`.
- Only nodejs and its own libraries move in the lock.

**Never:**
- Never run `pixi update`; a package the re-solve moves is held for one lock and released, not pinned.

## Acceptance Criteria

**Given** the manifest, the lock, the docs-site files and the workflows
**When** `target-version-check` reads them
**Then** every environment that carries nodejs locks 24.22.3 on every platform, and the check exits 0

- **AC1 — One nodejs everywhere.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild target-version-check
  ```

- **AC2 — The rules are held by tests.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_target_version_check_surfaces.py -q
  ```

</intent-contract>

## Result (2026-11-27)

- The lock holds nodejs 24.22.3 in all 58 environment-platform pairs that carry it, and no other nodejs record. Beyond nodejs, only its own libraries moved: `c-ares`, `libnghttp2`, `icu` and the `libbrotli*` and `libabseil` builds it dropped. `playwright` now sits at one version, 1.64.0, in every pair.
- The first solve also took `bmad-module-skill-forge` 12.0.0 in `bmad-suite-full`, `playwright` 1.65.1 in `mcp-host` and `pnpm` 12.24.0. Each was held at its locked version for one lock and released in the next; pixi kept the held versions.
- `.nvmrc` is `24.22.3` (its sha256 in `docs-site/README.md` follows), `engines.node` is `24.22.3`, and the pin policy's nodejs hold is an exact `24.22.3.*` on the `node` feature in place of a `<27.0` cap on four features. The library catalog names the declaration.
- `test_docs_site.py` reads the declaration: `.nvmrc` equals it, and the `site` environment composes `node` where the `site` feature used to copy the pin.
- `target-version-check` reds a second nodejs declaration, an environment that locks nodejs without `node`, a lock on another nodejs, a docs-site file naming another, and an `actions/setup-node` step. Eight new cases hold these rules together with Story 149.3's pixi rule.
- AC1: exit 0. AC2: 52 passed.
