---
title: "21.4: opengrep is repackaged from its release binaries as a local-only recipe"
type: 'feature'
created: '2026-09-28'
status: 'backlog'
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - recipes/cyclonedx-cli/recipe.yaml
  - recipes/ccusage/recipe.yaml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Warden will adopt `opengrep`, the open fork of the Semgrep static-analysis engine. It has no conda package
anywhere: neither `opengrep` nor `semgrep` is on conda-forge, and no `conda-forge/opengrep-feedstock` exists (checked
live on 2026-09-28). Upstream facts, checked on 2026-09-28:

- `opengrep/opengrep` v1.30.0, released 2026-09-07. `v1.30.1-candidate` and the `v2.0.0-nopython` alphas are
  prereleases and are not used.
- `COPYRIGHT` grants the LGPL "version 2.1", so the SPDX license is `LGPL-2.1-only`, an OSI license.
- The release ships self-contained binaries per platform: `opengrep_manylinux_x86` (46.5 MB), `opengrep_manylinux_aarch64`,
  `opengrep_osx_x86`, `opengrep_osx_arm64` and `opengrep_windows_x86.exe`. Each has a cosign `.sig` and `.cert`. There
  is no checksum file.
- The v1.x binary embeds its Python CLI, so it is a single-file executable with an embedded payload.

A source build is not feasible on conda-forge today:
- It needs OCaml 5.5.0 (the `Makefile`; the opam floor is 5.2.1), and conda-forge's `ocaml` tops out at 5.4.0.
- `dune` is not on conda-forge.
- `opam/semgrep.opam` carries 69 opam dependencies, none of them conda packages.
- `dune-project` pins `memprof-limits` to a git URL on a gitlab fork branch, which is not reproducible.
- 40 git submodules (the tree-sitter grammars) are missing from GitHub archives.
- It also needs the Python CLI wrapper.

The operator ruled on 2026-09-28: package it, and where only a binary repack is possible the recipe stays local and
records why.

**Approach:** author `recipes/opengrep/recipe.yaml` (v1) through `conda-forge-expert` as a per-platform binary repack
in the shape of `recipes/cyclonedx-cli` (G44), not noarch.
- One `if:` source per conda subdir, with `file_name: opengrep` (`opengrep.exe` on Windows) and a streamed sha256 per
  asset.
- No compiler and no `stdlib`.
- `build.dynamic_linking.binary_relocation: false`, because rattler-build's default relocation can corrupt a
  single-file binary with an embedded payload (G101). The test compares the packaged binary byte for byte with the
  release asset.
- Ship `LICENSE` and `COPYRIGHT` in-recipe from the v1.30.0 tag, since the bare binaries carry none (license pattern 2).
- The CFE block records `cfe-source-kind: github-release-binary`,
  `cfe-on-conda-forge-status: blocked-pending-prerequisites`, and each source-build blocker above in
  `cfe-forge-blocker-list`, so the recipe stays local.

Ledger key: `21-4-opengrep-is-repackaged-from-its-release-binaries-as-a-local-only-recipe`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-31 (FR-53); AD-1; AD-15.
- `spec-fleet-stewardship` governs `recipes/**` (coverage only); `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Downstream: Warden mints rows blocked on this story (mason 21.4). Unblocking them is the operator's flip.

## Acceptance Criteria

- Given `recipes/opengrep/recipe.yaml` When it is read Then it is per-platform (no `noarch`) with one `if:` source per
  subdir (linux-64, linux-aarch64, osx-64, osx-arm64, win-64) at `version: "1.30.0"`, each with its own computed
  sha256, and declares no compiler
- Given the build When it runs Then `build.dynamic_linking.binary_relocation` is `false`, and the unix binary lands at
  `${PREFIX}/bin/opengrep` with its execute bit set
- Given `pixi run -e local-recipes recipe-build recipes/opengrep` When it runs on linux-64 Then it exits 0
- Given the recipe's test When it runs Then `opengrep --version` reports `1.30.0`, and `opengrep scan` with a local
  rule file finds the one planted match in a fixture file, with no network access and with telemetry and
  version checks off
- Given the built artifact When `bin/opengrep` is hashed Then its sha256 equals the release asset's
- Given `about:` When it is read Then `license: LGPL-2.1-only` and `license_file` ships the tag's `LICENSE` and
  `COPYRIGHT`
- Given the CFE block When it is read Then `cfe-source-kind: github-release-binary`, `cfe-noarch: compiled`,
  `cfe-on-conda-forge-status: blocked-pending-prerequisites`, and `cfe-forge-blocker-list` naming each source-build
  blocker with its date
- Given `validate_recipe`, `optimize_recipe` and the CI-parity lint When they run Then none reports an error
- Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands a CFE `CHANGELOG.md`
  semver entry

## Tasks

1. Invoke `conda-forge-expert` (Rule 1). Re-verify on the day:
   - the latest non-prerelease tag (G109; if it is past v1.30.0, repackage the newest);
   - the asset names;
   - `opengrep`'s absence from live `channeldata.json`;
   - each source-build blocker (the OCaml version on conda-forge, `dune`, the opam pin, the submodules). If all of
     them have cleared, stop and report: a source build becomes possible and the operator decides.
2. Author `recipes/opengrep/recipe.yaml` from the `recipes/cyclonedx-cli` shape.
   - Stream each asset's sha256 (`curl -sL <url> | sha256sum`), and verify the cosign signature where `cosign` is
     available.
   - Add `LICENSE` and `COPYRIGHT` from the tag, and a fixture rule plus a source file under the recipe for the test.
   - Put the CFE block at the bottom.
3. Write the test.
   - A script test runs `opengrep --version` and an offline `opengrep scan --config <fixture rule> <fixture file>`,
     asserting the one match.
   - A second step compares the packaged binary's sha256 with the recorded asset hash.
   - Use a script test, not `package_contents` alone. G101: a green `npm install` or copy proves nothing about the
     binary.
4. Gates: `pixi run -e local-recipes validate recipes/opengrep`, `pixi run -e local-recipes lint-optimize recipes/opengrep`,
   and the CI-parity lint.
5. Build with `pixi run -e local-recipes recipe-build recipes/opengrep`. Confirm from the artifact (G85) and stamp
   `cfe-local-build-*`. The other four subdirs are hash-verified but not executed locally; say so in the CFE comments.
6. Close with the Rule-2 retro in its own `retro(cfe):` commit. Record whether relocation touched the binary (confirm
   or extend G101) and the OCaml-toolchain gap as source-build evidence.
7. Reconcile every Spec `spec-surface-check` names: memlog first, `git add`, then a scoped stamp for each.

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert`; the skill wins on any conflict and the story records the deviation.
- Keep the recipe local, with the reason in its CFE block, while a source build stays infeasible.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not open a staged-recipes, feedstock or upstream PR (a binary repack of an OSI project is a reviewer-scrutiny
  case, and there is no ask).
- Do not use a prerelease asset.
- Do not attempt an opam-at-build-time source build inside this story. That would be a separate, operator-ruled effort.
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml` or `pixi.lock`; Warden wires the adoption.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | v1.30.0 assets | `--version` 1.30.0; the planted match is found | — |
| relocation corrupts | default `binary_relocation` | the packaged binary differs from the asset, or crashes | `binary_relocation: false`; the byte-compare test fails otherwise (G101) |
| network reach | a scan phones home for rules or metrics | the test must not depend on it | a local `--config` with telemetry and version checks off; offline build sandbox |
| musl vs glibc | musllinux asset chosen for linux | may not run on the conda sysroot | use the `manylinux` asset |
| newer release | a tag past v1.30.0 | repackage the newest | G109 |
| source becomes feasible | conda-forge gains OCaml 5.5 and `dune` | stop and report | the operator rules on a source-build story |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-31 (FR-53).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-28 (night) — Proposed: Mason packages the intake
toolchain*.
Ledger key: `21-4-opengrep-is-repackaged-from-its-release-binaries-as-a-local-only-recipe`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: `flag-exempt: recipe-build`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code).

**Manual checks:**
- `pixi run -e local-recipes recipe-build recipes/opengrep` — exit 0 on linux-64; the test phase shows `1.30.0`, the
  planted match and the matching sha256.
- `pixi run -e local-recipes validate recipes/opengrep` and `pixi run -e local-recipes lint-optimize recipes/opengrep`
  — no errors.
- `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/opengrep` — no lint
  (G65).
- The CFE block reads `cfe-on-conda-forge-status: blocked-pending-prerequisites` and names the source-build blockers.
- The story's CFE-surface commits: exactly one, subject `retro(cfe):`, carrying `CHANGELOG.md`.
- `pixi run -e pyforge-guild spec-surface-check` — exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate); the operator reviews the branch before
  landing it as `Merge pyforge-mason/21-4-opengrep-is-repackaged-from-its-release-binaries-as-a-local-only-recipe into main`.
