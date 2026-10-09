---
title: "21.3: gitgres builds green against PostgreSQL 17 from a pinned commit"
type: 'feature'
created: '2026-09-28'
status: 'in-progress'
baseline_revision: '1560c1fbcf187bcf729be8aff1705b0ffb3687e6'
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/templates/c-cpp/autotools-recipe.yaml
  - recipes/postgresql/recipe.yaml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `gitgres` stores git objects and refs in PostgreSQL tables. The operator ruled on 2026-09-28 to package
it as a design reference that nothing in the platform loads, built against PostgreSQL 17 only (fnd:CAP-12). It has no
conda package anywhere: no `gitgres` on conda-forge and no `conda-forge/gitgres-feedstock` (both checked live on
2026-09-28). Upstream facts, checked on 2026-09-28:

- `andrew/gitgres` is MIT-licensed C with no tags or releases. HEAD is `eaf8743f2c137d61a75432e44e13467cad7eceaa`
  (2026-03-08, "Update README to reflect extension as primary setup path"), which was also the last push.
- `ext/` is a PGXS extension: `ext/Makefile` includes `$(PG_CONFIG) --pgxs`. `gitgres.control` has
  `default_version = '0.1'`, `requires = 'pgcrypto'` and `module_pathname = '$libdir/gitgres'`, and the module links
  OpenSSL through `pkg-config`.
- `backend/` builds `gitgres-backend` and `git-remote-gitgres` against libgit2 (through `pkg-config`) and `-lpq`. Its
  Makefile hard-codes `CC = cc` and has no install target.
- `gitgres-backend` with no arguments prints `Usage: gitgres-backend <command> [args]`.
- The upstream Dockerfile builds `FROM postgres:17` with `postgresql-server-dev-17` and `libgit2-dev`.
- conda-forge-pinning pins `postgresql: 18` and `libpq: 18` globally. The estate holds 17 (`pixi.toml` pins
  `postgresql >=17.11,<18` and `libpq >=17.11,<18`).
- conda-forge's `postgresql` ships `pg_config`, the PGXS makefiles and the `pgcrypto` contrib extension.

**Approach:** author `recipes/gitgres/recipe.yaml` (v1) through `conda-forge-expert` as a compiled, per-platform
recipe. With no upstream tag, it is a dev snapshot pinned at that commit: `version: "0.1.0.dev0"`, following the
control file's `0.1`, with `context.commit` and the `archive/<commit>.tar.gz` source. Record in the CFE block that the
recipe flips to the tag archive when upstream tags (G109).
- Build requirements: `compiler("c")`, `stdlib("c")`, `make` and `pkg-config`.
- Host requirements: `postgresql >=17.11,<18`, `libpq >=17.11,<18`, `libgit2` and `openssl`, all explicit so the global
  18 pin cannot apply. If the rendered variant still resolves 18, add a recipe-local `conda_build_config.yaml` holding
  `postgresql: ['17']` and `libpq: ['17']`. A recipe-specific key is legitimate (G47).
- The build script runs `make -C ext PG_CONFIG="${PREFIX}/bin/pg_config"` and `make -C ext install` with the same
  `PG_CONFIG`, with `PKG_CONFIG_PATH` pointed at `${PREFIX}/lib/pkgconfig`. It then runs
  `make -C backend CC="${CC}" PG_CONFIG="${PREFIX}/bin/pg_config"` and copies both backend binaries into `${PREFIX}/bin`.
- `build.skip: win`: PGXS does not build on Windows (G102).
- Run requirements: `postgresql >=17.11,<18`, because the extension module is tied to the server's major version.

Ledger key: `21-3-gitgres-builds-green-against-postgresql-17-from-a-pinned-commit`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-31 (FR-53); fnd:CAP-12 (the estate holds PostgreSQL 17); AD-1; AD-15.
- `spec-fleet-stewardship` governs `recipes/**` (coverage only); `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.

## Acceptance Criteria

- Given `recipes/gitgres/recipe.yaml` When it is read Then it starts with the v1 schema header, sources
  `https://github.com/andrew/gitgres/archive/${{ commit }}.tar.gz` with
  `commit: eaf8743f2c137d61a75432e44e13467cad7eceaa` and a computed sha256, and declares `compiler("c")` with
  `stdlib("c")`
- Given the host and run requirements When the recipe renders on linux-64 Then `postgresql` and `libpq` resolve to 17.x
  (`>=17.11,<18`) in the build, host and test environments, and never to 18
- Given `pixi run -e local-recipes recipe-build recipes/gitgres` When it runs on linux-64 Then it exits 0 and the
  artifact carries `lib/gitgres${SHLIB_EXT}`, `share/extension/gitgres.control`,
  `share/extension/gitgres--0.1.sql`, `bin/gitgres-backend` and `bin/git-remote-gitgres`
- Given the recipe's test When it runs Then it initdbs a throwaway cluster on a Unix socket in a temporary directory,
  starts it, runs `CREATE EXTENSION gitgres CASCADE`, which also creates `pgcrypto`, runs one query against a table the
  extension creates, and stops the cluster; and `gitgres-backend` with no arguments prints its usage line
- Given Windows When the recipe renders Then it is skipped (`build.skip: win`)
- Given `validate_recipe`, `optimize_recipe` and the CI-parity lint When they run Then none reports an error
- Given the CFE block When it is read Then `cfe-source-kind: github-commit`, `cfe-noarch: compiled`, a note that
  nothing in the platform loads the extension, and the `cfe-local-build-*` fields match the real build
- Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands a CFE `CHANGELOG.md`
  semver entry

## Tasks

1. Invoke `conda-forge-expert` (Rule 1). Re-verify on the day:
   - that upstream still has no tag (G109; if one exists, source the tag archive and version from it);
   - the HEAD commit;
   - `gitgres`'s absence from live `channeldata.json` (G58, G74);
   - the conda-forge `postgresql` 17.x build that `>=17.11,<18` resolves.
2. Author `recipes/gitgres/recipe.yaml` and `build.sh`.
   - Stream the commit archive's sha256; G61 warns that GitHub commit archives can re-gzip, so recompute on any
     mismatch.
   - Point `pkg-config` at the host prefix.
   - Override the backend's `CC` from the command line; copy the two backend binaries by hand.
   - Put the CFE block at the bottom.
3. Write the test as a `script:` that uses only the test environment's PostgreSQL 17: `initdb`, `pg_ctl -w start` with
   `-c listen_addresses=''` and `-k <tmp>`, `psql -h <tmp>`, and `pg_ctl stop`. It must not use the network or TCP.
   Add `package_contents` for the installed files.
4. Gates: `pixi run -e local-recipes validate recipes/gitgres`, `pixi run -e local-recipes lint-optimize recipes/gitgres`,
   `pixi run -e local-recipes check-deps recipes/gitgres`,
   `pixi run -e local-recipes scan-vulnerabilities recipes/gitgres`, and the CI-parity lint.
5. Build with `pixi run -e local-recipes recipe-build recipes/gitgres`. Confirm from the artifact and
   `rattler-build test --package-file` (G85), check that the resolved `postgresql` is 17.x, and stamp
   `cfe-local-build-*`.
6. Close with the Rule-2 retro in its own `retro(cfe):` commit. Record the PGXS-under-conda findings (the global 18 pin
   and `PG_CONFIG` from the host prefix), and add a gotcha if one generalizes.
7. Reconcile every Spec `spec-surface-check` names: memlog first, `git add`, then a scoped stamp for each.

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert`; the skill wins on any conflict and the story records the deviation.
- Hold PostgreSQL 17: `>=17.11,<18` for `postgresql` and `libpq`, in every environment the recipe renders.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not build, test or pin against PostgreSQL 18, and do not lift any psycopg or pgvector cap to make a solve work
  (fnd:CAP-12, AGENTS.md § Policy).
- Do not wire `gitgres` into the platform, `pixi.toml`, `pixi.lock` or any station; it stays a design reference.
- Do not touch `src/shared/packages/pyforge-mason/`.
- Do not open a staged-recipes, feedstock or upstream PR.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | commit `eaf8743f`, host PG 17 | extension created; backend prints usage | — |
| global pin leaks | the rendered host shows `postgresql 18.*` | build refused | add the recipe-local CBC `postgresql: ['17']`, `libpq: ['17']` |
| `cc` not found | backend Makefile `CC = cc` | build fails | pass `CC="${CC}"` on the make command line |
| pgcrypto missing | test env PostgreSQL without contrib | `CREATE EXTENSION … CASCADE` fails | the test fails the build; verify contrib ships in the conda package |
| checksum drift | GitHub re-gzips the commit archive | fetch fails on sha256 | recompute (G61) |
| upstream tags | a tag appears before the build | source the tag, version from it | G109 |
| Windows | win-64 render | skipped | `build.skip: win` |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-31 (FR-53).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-28 (night) — Proposed: Mason packages the intake
toolchain*.
Ledger key: `21-3-gitgres-builds-green-against-postgresql-17-from-a-pinned-commit`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: `flag-exempt: recipe-build`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code).

**Manual checks:**
- `pixi run -e local-recipes recipe-build recipes/gitgres` — exit 0 on linux-64; the test phase shows
  `CREATE EXTENSION` succeeding and the backend's usage line.
- The build log's resolved host and test environments list `postgresql 17.*` and `libpq 17.*`, and no 18.
- `pixi run -e local-recipes validate recipes/gitgres` and `pixi run -e local-recipes lint-optimize recipes/gitgres`
  — no errors.
- `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/gitgres` — no lint (G65).
- The story's CFE-surface commits: exactly one, subject `retro(cfe):`, carrying `CHANGELOG.md`.
- `pixi run -e pyforge-guild spec-surface-check` — exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate); the operator reviews the branch before
  landing it as `Merge pyforge-mason/21-3-gitgres-builds-green-against-postgresql-17-from-a-pinned-commit into main`.
