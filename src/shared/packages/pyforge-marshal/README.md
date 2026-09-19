# pyforge-marshal

General documentation (architecture, operations, how-tos): docs/MAP.md at the repository root.

Deterministic BMAD-loop supervisor CLI (`marshal`) wrapping
[`bmad-loop`](https://github.com/bmad-code-org/bmad-loop) with gates-as-objects,
run supervision, landing, fleet status, and adapter portability — built on a
closed verdict lattice and a coded finding registry.

The same package ships **Genesis** — the seed installer (`marshal seed …`) that
delivers this repository's operating model (Dream-first tiers, BMAD layout,
detectors, agent entry files) into another git repo. **Genesis installs the
machinery; Marshal operates it.**

## Documentation

| Doc | Audience |
|---|---|
| [Adoption guide](docs/adoption-guide.md) | First-time adopters — brownfield dry-run → apply → CI |
| [Finding → remedy reference](docs/finding-remedy-reference.md) | Operators fixing `marshal seed check` output |
| [Managed region contract](docs/managed-region-contract.md) | Authors editing hybrid files with marker spans |
| [Air-gapped deployment](docs/air-gapped-deployment.md) | Offline conda mirrors — in-package templates, no runtime fetch |

Planning artifacts:
[`_bmad-output/projects/pyforge-marshal/planning-artifacts/`](../../../../_bmad-output/projects/pyforge-marshal/planning-artifacts/)

## Genesis — four verbs

| Verb | Purpose | Typical use |
|---|---|---|
| **`init`** | Greenfield install into an empty directory | `marshal seed init ./my-repo --slug my-project --agents claude,cursor` |
| **`adopt`** | Brownfield layer onto an existing repo (dry-run by default) | `marshal seed adopt --repo-root . --agents claude,cursor` then `--apply --yes` |
| **`check`** | Read-only conformance report (CI gate) | `marshal seed check --repo-root . --strict` |
| **`update`** | Upgrade to a newer bundled `model_version` | `marshal seed update --repo-root . --yes` |

Helper verbs (read-only): `marshal seed explain <artifact-id>`,
`marshal seed version`.

### Worked examples

**Greenfield** — provision a new repo tree:

```bash
marshal seed init /path/to/empty-dir --slug pyforge-scribe --agents claude,cursor
marshal seed check --repo-root /path/to/empty-dir
```

**Brownfield** — review then apply:

```bash
cd /path/to/existing-repo
marshal seed adopt --repo-root . --agents claude,cursor          # dry-run plan
marshal seed adopt --repo-root . --agents claude,cursor --apply --yes
marshal seed check --repo-root . --strict
```

**Upgrade** when a newer Genesis release ships:

```bash
marshal seed update --repo-root . --yes
```

## Five artifact classes

Every manifest entry is classified (see [adoption guide](docs/adoption-guide.md)):

| Class | Reader takeaway |
|---|---|
| **referenced** | Verified upstream dependency — not copied into the repo |
| **copied-managed** | Tool-owned whole file — do not hand-edit |
| **copied-seeded** | Installed once as a starter — repo-owned forever after |
| **generated-derived** | Recomputed from contract/state — safe to regenerate |
| **hybrid-managed-region** | Repo-owned file, tool-owned marker span — see [managed region contract](docs/managed-region-contract.md) |

## Two version numbers

| Version | Meaning |
|---|---|
| **`model_version`** | Operating model semver in the bundled manifest and `.marshal/seed-state.yml` |
| **`seed_model_version`** | Genesis package release that last wrote state |

`marshal seed version --repo-root .` prints both. `model-behind` means run `marshal seed update`.

## State file

Genesis records install truth in **`.marshal/seed-state.yml`** — managed hashes,
opt-outs, skips, legacy paths, and applied migrations. Never hand-edit; restore
from git or rebuild with `marshal seed adopt` if corrupt (`state-invalid` finding).

## Develop

Run from the repository root (the parent pixi workspace):

```bash
pixi run -e pyforge-marshal pyforge-marshal-test         # run the test suite
pixi run -e pyforge-marshal marshal --version             # console-script smoke test
pixi run -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache  # AD-3/AD-4 contracts

pixi run -e pyforge-marshal pyforge-marshal-build-conda   # .conda package via pixi-build-python
pixi run -e pyforge-marshal pyforge-marshal-build-dist    # wheel + sdist via `python -m build`
pixi run -e pyforge-marshal pyforge-marshal-build         # both of the above
pixi run -e pyforge-marshal pyforge-marshal-smoke         # marshal --help/--version against the INSTALLED artifact
```

The `pyforge-marshal` environment is lean by design (`no-default-feature`): built
package, conda run-dependencies, build toolchain, pytest, and import-linter.

## Platforms

Build and smoke targets: `linux-64` and `osx-arm64`. Windows support is
WSL-first — run Marshal inside WSL rather than as a native `win-64` build.
