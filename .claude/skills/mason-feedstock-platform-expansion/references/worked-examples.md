# Worked Examples

Append each completed case as its own H2 section below. A case carries
the resolved Parameters, the empirical state at the time, the resolved
Open Questions, any per-case risks, and the final PR URL once the
effort closes.

---

## Worked Example: cocoindex 1.0.10 → +osx_arm64, +linux_aarch64 (2026-06-14)

| Parameter | Resolved value |
|---|---|
| `feedstock` | `cocoindex` |
| `upstream_version` | `1.0.10` |
| `current_platforms` | `linux-64`, `osx-64`, `win-64` (35 builds × 3 platforms = 105 artifacts at 1.0.10) |
| `target_platforms` | `osx_arm64`, `linux_aarch64` |
| `recipe_shape` | `compiled` (Rust+PyO3 via maturin) |
| `fork_owner` | `rxm7706` |
| `branch_name` | `add-osx-arm64-linux-aarch64` |
| `recipe_path` | `recipes/cocoindex/` |
| `local_test_subdir` | `linux-64` |

**Status**: Draft v1 (2026-06-14) — Open Questions Q1–Q5 resolved
inline below; ready for BMAD intake.

**Driven by**: cocoindex not installable on macOS arm64 — confirmed
empirically:
`curl https://conda.anaconda.org/conda-forge/osx-arm64/repodata.json | grep cocoindex-`
returns zero matches. The local recipe at `recipes/cocoindex/recipe.yaml`
is also stale at 1.0.5 — a drift that should close in the same effort.

**Predecessor**: cocoindex PR #33231 (May 2026 — original conda-forge
submission; landed the tree-sitter + GCC 14 + glibc 2.17 sysroot fix
per skill gotcha **G1**). The recipe already carries cross-compile
scaffolding (`requirements.build:` includes the `if: build_platform !=
target_platform / then: [python, cross-python_${{ target_platform }},
crossenv, maturin]` block), so the recipe code itself is ready for
`osx_arm64` and `linux_aarch64`; the gap is in `conda-forge.yml`.

### Empirical state (verified 2026-06-14)

```
upstream conda-forge/cocoindex-feedstock main: version 1.0.10, sha256 d2d04f6f...
upstream platforms shipping: linux-64 (35), osx-64 (35), win-64 (35)
upstream platforms missing:  osx-arm64 (0), linux-aarch64 (0)
local recipes/cocoindex/recipe.yaml: version 1.0.5 (stale by 4 patches + 1 minor)
rxm7706/cocoindex-feedstock: fork exists, parented to conda-forge/cocoindex-feedstock
```

Upstream `conda-forge.yml` (verbatim, 2026-06-14):
```yaml
github:
  branch_name: main
  tooling_branch_name: main
conda_build:
  error_overlinking: true
conda_forge_output_validation: true
bot:
  automerge: true
  inspection: update-grayskull
  check_solvable: true
  run_deps_from_wheel: true
conda_install_tool: pixi
conda_build_tool: rattler-build
```

→ Deltas this PR needs:

| Delta | Why |
|---|---|
| Add `workflow_settings.store_build_artifacts: true` (replaces deprecated `azure.store_build_artifacts`) | Per CFE `conda-forge-yml-reference.md` § "Top use cases" — keeps `.conda` artifacts downloadable from CI for reviewer smoke-testing. Default is `[]` (empty list = off) |
| Add `provider.osx_arm64: default` + `provider.linux_aarch64: default` | Activates the two new CI legs. `default` resolves to Azure (per skill ecosystem-update note, Mar 2026 GHA opt-in is `linux_64`-only) |

The remaining keys (`error_overlinking`, `bot.automerge`, etc.) are
already upstream and do not need to be re-added.

### Open Questions — resolved 2026-06-14

**Q1. `noarch_platforms` in the user's intake YAML — keep, drop, or
reinterpret?** The intake message proposed
`noarch_platforms: [win_64, linux_64, osx_64]`, but cocoindex is a
**compiled** Rust+PyO3 package, not noarch. Per CFE skill **G12**,
`noarch_platforms` is the conda-smithy escape hatch for noarch:python
recipes with platform-conditional `run:` selectors; it does not
control the build matrix of a compiled recipe.
**Resolution**: interpret as "expand the build matrix" → translate to
`provider.osx_arm64: default` + `provider.linux_aarch64: default`.
Drop `noarch_platforms` from the final `conda-forge.yml`.

**Q2. PR target — `staged-recipe/cocoindex-feedstock` typo?** No
`staged-recipe` org exists; cocoindex is a feedstock, not a
staged-recipes submission.
**Resolution**: `conda-forge/cocoindex-feedstock`.

**Q3. Scope — just osx-arm64 + linux-aarch64?** Original intake
listed 9 conda subdirs. `noarch`, `unix`, `linux`, `osx`, `win` are
not conda subdirs; cocoindex is compiled so noarch is impossible (see
Q1). `linux-ppc64le`, `linux-s390x`, `linux-riscv64`, `win-arm64` have
insufficient transitive-Rust-dep coverage on conda-forge in mid-2026
— adding them would produce immediate red CI on dep resolution.
**Resolution**: osx-arm64 + linux-aarch64 only.

**Q4. Local cross-target build attempts — gate or diagnostic?**
**Resolution**: diagnostic only. The recipe's cross-compile
scaffolding has been proven by upstream CI for the existing 3
platforms; logically extensible without recipe changes.

**Q5. Operator-confirm gates — explicit halt or automated proceed?**
**Resolution**: both halts (S10 + S12) mandatory. PR creation against
the upstream conda-forge org is stakeholder-visible. Operator-confirms-once
is not sufficient given the multi-day Azure CI cycle.

### Per-case Pre-Resolved Decisions

- **Branch name**: `add-osx-arm64-linux-aarch64`. Single descriptive
  name; no version suffix needed.
- **Commit message**: single commit,
  `"Add osx_arm64 + linux_aarch64; enable workflow_settings.store_build_artifacts"`.
- **PR opens as DRAFT.** Not ready-for-review until operator confirms
  CI is green on all 5 legs.

### Per-case Risks (additive to guide § Risk catalog)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| osx-arm64 CI fails because a transitive Rust dep isn't built for osx-arm64 yet | Low | Blocks the PR | Pre-check via `check_dependencies(target_subdir="osx-arm64")` before opening the PR; if a gap exists, document the prerequisite feedstock that needs to ship first |
| `error_overlinking: true` (already upstream) surfaces previously-tolerated overlinks on the two new platforms | Medium | Blocks PR until fixed | Treat as Stop-the-Line per Build Failure Protocol. Fix by tightening `host:` deps; `build.missing_dso_whitelist` last resort |

### Final state

- Draft PR URL: _<populate when S11 lands>_
- Merge date: _<populate when S12 closes>_
- First `cocoindex-1.0.10-*` on `osx-arm64/repodata.json`: _<populate>_
- First `cocoindex-1.0.10-*` on `linux-aarch64/repodata.json`: _<populate>_
- Closeout retro CHANGELOG entry: _<populate>_
