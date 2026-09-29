---
title: "21.2: forge builds green from source as a local recipe"
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

**Problem:** Warden will adopt `forge`, the CLI and Go library that talks to GitHub, GitLab, Gitea/Forgejo and
Bitbucket Cloud through one interface. It has no conda package anywhere: no `forge` on conda-forge and no
`conda-forge/forge-feedstock` (both checked live on 2026-09-28). Upstream facts, checked on 2026-09-28:

- `git-pkgs/forge` v0.10.0, released 2026-09-02, MIT, Go.
- `go.mod` declares `go 1.26.0` and `toolchain go1.26.7`. conda-forge's `go-nocgo` is at 1.27.1.
- `.goreleaser.yml` builds `main: ./cmd/forge` into `binary: forge` with `CGO_ENABLED=0`, and injects
  `-X github.com/git-pkgs/forge/internal/cli.Version`.
- The variable defaults to `"dev"`. The `forge version` subcommand prints `forge <Version>`, so a build that misses the
  ldflag ships `forge dev`.

`forge` is a generic name, so a later conda-forge package could take it for something else (CFE G118). The operator
ruled on 2026-09-28: package it. Packaging is not adopting, and a green local build ends the story.

**Approach:** author `recipes/forge/recipe.yaml` (v1) through `conda-forge-expert`. Model it on the Go template and
`recipes/wuphf`, with the tag archive as source.
- Build `./cmd/forge` with `compiler("go-nocgo")`, `CGO_ENABLED=0` and `GOTOOLCHAIN=local`.
- Set `-ldflags "-s -w -X github.com/git-pkgs/forge/internal/cli.Version=${PKG_VERSION}"`.
- Bundle the dependency licenses with `go-licenses save ./cmd/forge`.
- Add a Windows branch (`build.bat`).

The test asserts the exact version string, so a missed ldflag cannot pass.

Ledger key: `21-2-forge-builds-green-from-source-as-a-local-recipe`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-31 (FR-53); AD-1; AD-15.
- `spec-fleet-stewardship` governs `recipes/**` (coverage only); `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Downstream: Warden adopts `forge`.

## Acceptance Criteria

- Given `recipes/forge/recipe.yaml` When it is read Then it starts with the v1 schema header, sources
  `https://github.com/git-pkgs/forge/archive/refs/tags/v${{ version }}.tar.gz` at `version: "0.10.0"` with a computed
  sha256, and builds `./cmd/forge` with `compiler("go-nocgo")`
- Given the build When it runs Then `CGO_ENABLED=0` and `GOTOOLCHAIN=local` are set and the version is injected
  through `github.com/git-pkgs/forge/internal/cli.Version`
- Given `pixi run -e local-recipes recipe-build recipes/forge` When it runs on linux-64 Then it exits 0
- Given the recipe's test When it runs Then `forge version` prints exactly `forge 0.10.0`, and `package_contents`
  finds `bin/forge`
- Given `validate_recipe`, `optimize_recipe` and the CI-parity lint When they run Then none reports an error
- Given the name `forge` When the story starts Then live `channeldata.json` still shows no `forge` package, and the
  check is recorded with its date in the CFE comments block
- Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands a CFE `CHANGELOG.md`
  semver entry

## Tasks

1. Invoke `conda-forge-expert` (Rule 1). Re-verify the latest non-prerelease tag (G109), `go.mod`, the goreleaser
   ldflags, and `forge`'s absence from live conda-forge `channeldata.json` (G58, G74, G118).
2. Author `recipes/forge/recipe.yaml`, `build.sh` and `build.bat`.
   - Stream the archive's sha256.
   - Run `go-licenses save ./cmd/forge --save_path library_licenses` (G79 on any per-OS fatal).
   - Put the CFE block at the bottom.
3. Gates: `pixi run -e local-recipes validate recipes/forge`, `pixi run -e local-recipes lint-optimize recipes/forge`,
   `pixi run -e local-recipes scan-vulnerabilities recipes/forge`, and the CI-parity lint.
4. Build with `pixi run -e local-recipes recipe-build recipes/forge`, confirm from the artifact (G85), and stamp
   `cfe-local-build-*`.
5. Close with the Rule-2 retro in its own `retro(cfe):` commit: the `CHANGELOG.md` entry and version carriers; PATCH if
   the guidance held, MINOR for a new gotcha, which also regenerates `config/failure-catalog.yaml`.
6. Reconcile every Spec `spec-surface-check` names: memlog first, `git add`, then a scoped stamp for each.

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert`; the skill wins on any conflict and the story records the deviation.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not open a staged-recipes, feedstock or upstream PR.
- Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not ship a build whose `forge version` reads `forge dev`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | tag v0.10.0 | `forge version` → `forge 0.10.0` | — |
| missing ldflag | no `-X …internal/cli.Version` | `forge dev` | the version test fails the build |
| toolchain directive | `toolchain go1.26.7`, compiler 1.27.x | builds with the local compiler | `GOTOOLCHAIN=local`, never a download |
| name collision | a `forge` package appears on conda-forge | stop; compare the artifacts (G118) | report to the operator before renaming |
| newer upstream | a tag past v0.10.0 exists | package the newest; note it in the retro | G109 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-31 (FR-53).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-28 (night) — Proposed: Mason packages the intake
toolchain*.
Ledger key: `21-2-forge-builds-green-from-source-as-a-local-recipe`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: `flag-exempt: recipe-build`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code).

**Manual checks:**
- `pixi run -e local-recipes recipe-build recipes/forge` — exit 0 on linux-64; the test phase shows `forge 0.10.0`.
- `pixi run -e local-recipes validate recipes/forge` and `pixi run -e local-recipes lint-optimize recipes/forge` — no
  errors.
- `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/forge` — no lint (G65).
- The story's CFE-surface commits: exactly one, subject `retro(cfe):`, carrying `CHANGELOG.md`.
- `pixi run -e pyforge-guild spec-surface-check` — exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate); the operator reviews the branch before
  landing it as `Merge pyforge-mason/21-2-forge-builds-green-from-source-as-a-local-recipe into main`.
