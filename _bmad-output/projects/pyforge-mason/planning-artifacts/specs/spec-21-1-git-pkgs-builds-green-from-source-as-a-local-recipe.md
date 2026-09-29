---
title: "21.1: git-pkgs builds green from source as a local recipe"
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
  - .claude/skills/conda-forge-expert/templates/go/pure-recipe.yaml
  - recipes/wuphf/recipe.yaml
  - recipes/wuphf/build.sh
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Warden and Atlas will adopt `git-pkgs`, the git subcommand that analyses package and dependency use across
a repository's history. It has no conda package anywhere: no `git-pkgs` on conda-forge and no
`conda-forge/git-pkgs-feedstock` (both checked live on 2026-09-28). Upstream facts, checked on 2026-09-28:

- `git-pkgs/git-pkgs` v0.20.0, released 2026-09-04, MIT, Go.
- `go.mod` declares `go 1.26.7`. conda-forge's `go-nocgo` is at 1.27.1.
- `.goreleaser.yaml` builds `main: .` into `binary: git-pkgs` with `CGO_ENABLED=0`, and injects
  `-X github.com/git-pkgs/git-pkgs/cmd.version`, `.commit` and `.date`.
- SQLite comes from the pure-Go `modernc.org/sqlite` and git access from `go-git`, so there is no cgo.
- The cobra root command wires `--version`.
- The repo ships `LICENSE` at the root. Releases carry per-platform tarballs and a `checksums.txt`, but a source build
  is the conda-forge norm for Go and is fully feasible here.

The operator ruled on 2026-09-28: package it. Packaging is not adopting, and a green local build ends the story.

**Approach:** author `recipes/git-pkgs/recipe.yaml` (v1) through `conda-forge-expert`. Model it on its Go template
(`templates/go/pure-recipe.yaml`) and the repo's pure-Go precedent (`recipes/wuphf`), with the tag archive as source.
- Build `.` with `compiler("go-nocgo")`, `CGO_ENABLED=0` and `GOTOOLCHAIN=local`, so no toolchain is downloaded.
- Set `-ldflags "-s -w -X github.com/git-pkgs/git-pkgs/cmd.version=${PKG_VERSION}"`.
- Bundle the dependency licenses with `go-licenses save`.
- Add a Windows branch (`build.bat`, `call` on shims) so the recipe is not unix-only by accident (G102).

Ledger key: `21-1-git-pkgs-builds-green-from-source-as-a-local-recipe`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-31 (FR-53); AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only
  in the `retro(cfe):` commit).
- `spec-fleet-stewardship` governs `recipes/**` (coverage only); `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Downstream: Atlas and Warden mint rows blocked on this story (mason 21.1). Unblocking them is the operator's flip.

## Acceptance Criteria

- Given `recipes/git-pkgs/recipe.yaml` When it is read Then it starts with the v1 schema header, sources
  `https://github.com/git-pkgs/git-pkgs/archive/refs/tags/v${{ version }}.tar.gz` at `version: "0.20.0"` with a
  computed sha256, and builds with `compiler("go-nocgo")` and no `stdlib`
- Given the build When it runs Then `CGO_ENABLED=0` and `GOTOOLCHAIN=local` are set, no Go toolchain is downloaded,
  and the version is injected through `github.com/git-pkgs/git-pkgs/cmd.version`
- Given `pixi run -e local-recipes recipe-build recipes/git-pkgs` When it runs on linux-64 Then it exits 0 and the
  artifact lands in `build_artifacts/`
- Given the recipe's test When it runs Then `git-pkgs --version` prints `0.20.0`, and `package_contents` finds
  `bin/git-pkgs`
- Given `validate_recipe`, `optimize_recipe` and `conda-smithy recipe-lint --conda-forge` through `pixi exec` When they
  run Then none reports an error; `optimize_recipe` warnings are fixed or justified in the CFE comments block
- Given `about:` When it is read Then `license: MIT` with `license_file` naming `LICENSE` and the bundled dependency
  licenses
- Given the CFE block When it is read Then `cfe-source-kind: github-tag`, `cfe-noarch: compiled`,
  `cfe-upstream-registry: golang`, and the `cfe-local-build-*` fields match the real build
- Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands a CFE `CHANGELOG.md`
  semver entry and its version carriers

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1). Re-verify upstream: the latest non-prerelease tag
   (G109: if it is past v0.20.0, package the newest and record why), `go.mod`'s `go` line, `.goreleaser.yaml`'s
   ldflags, and that `git-pkgs` is still absent from live conda-forge `channeldata.json` (G58, G74).
2. Author `recipes/git-pkgs/recipe.yaml`, `build.sh` and `build.bat` from the Go template.
   - Stream the archive's sha256 (`curl -sL <url> | sha256sum`); never trust a remembered hash.
   - Run `go-licenses save . --save_path library_licenses`, which lands in `license_file`. G79: a per-OS fatal on a
     dependency gets a per-OS `--ignore`, never `|| true`.
   - Put the CFE metadata block and every agent note in the bottom `#### CFE` block, never inline.
3. Gates, in order: `pixi run -e local-recipes validate recipes/git-pkgs`,
   `pixi run -e local-recipes lint-optimize recipes/git-pkgs`,
   `pixi run -e local-recipes scan-vulnerabilities recipes/git-pkgs`, and the CI-parity lint.
4. Build: `pixi run -e local-recipes recipe-build recipes/git-pkgs`.
   - `get_build_summary` can report "unknown" on a native success (G85). Confirm from the `.conda` artifact and
     `rattler-build test --package-file`.
   - Stamp the `cfe-local-build-*` fields from the real outcome.
5. Close with the Rule-2 retro in its own commit. Subject `retro(cfe): v<x.y.z> — …`, never starting `Story 21.1:`.
   - The commit carries the CFE `CHANGELOG.md` entry, the version in `SKILL.md`, `MANIFEST.yaml` and
     `config/skill-config.yaml`, and `config/failure-catalog.yaml` (`pixi run -e local-recipes generate-failure-catalog`)
     only when a new gotcha is added.
   - Bump PATCH if the guidance held, MINOR for a new gotcha.
   - The recipe files go in a separate commit.
6. Reconcile every Spec `spec-surface-check` names: memlog first, `git add`, then a scoped
   `--write-baseline --spec` for each (AGENTS.md checklist item 5).

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` for every recipe judgement; where this story and the skill disagree, the skill wins
  and the story records the deviation.
- Read every verdict from the exit code, never through a pipe.
- Keep `cfe-*` metadata in the local recipe (strip-on-push only happens if a PR is ever asked for; G62).

**Never:**
- Do not open a staged-recipes, feedstock or upstream PR (no explicit ask; a green local build ends the task).
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `environment.yaml`: packaging is not
  adopting. Warden and Atlas wire it on their own chains.
- Do not repackage the release tarballs; the source build is feasible.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | tag v0.20.0, `go-nocgo` 1.27.x | `git-pkgs --version` → `0.20.0` | — |
| missing ldflag | build without `-X …cmd.version` | version reads unknown or a pseudo-version | the test fails the build |
| toolchain download | `GOTOOLCHAIN` unset, `go.mod` above the compiler | Go tries to fetch a toolchain | `GOTOOLCHAIN=local` makes it fail loudly instead |
| newer upstream | a tag past v0.20.0 exists at build time | package the newest; note it in the retro | G109 |
| go-licenses fatal | a dependency's license unclassified on one OS | per-OS `--ignore <module>` | never `\|\| true` (G79) |
| name taken | `git-pkgs` appears on conda-forge | stop; mirror the feedstock instead (G58, G118) | report to the operator |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-31 (FR-53).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-28 (night) — Proposed: Mason packages the intake
toolchain*.
Ledger key: `21-1-git-pkgs-builds-green-from-source-as-a-local-recipe`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: `flag-exempt: recipe-build` (a recipe build ships no runtime capability behind a flag).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code, so the suite must stay green).

**Manual checks:**
- `pixi run -e local-recipes recipe-build recipes/git-pkgs` — exit 0 on linux-64; the test phase shows
  `git-pkgs --version` = `0.20.0`.
- `pixi run -e local-recipes validate recipes/git-pkgs` and `pixi run -e local-recipes lint-optimize recipes/git-pkgs`
  — no errors.
- `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/git-pkgs` — no lint
  (G65).
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert` — exactly one `retro(cfe):` subject, and
  that commit carries `CHANGELOG.md`.
- `pixi run -e pyforge-guild spec-surface-check` — exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate); the operator reviews the branch before
  landing it as `Merge pyforge-mason/21-1-git-pkgs-builds-green-from-source-as-a-local-recipe into main`.
