# Air-gapped deployment

Genesis is designed for environments where runtime `curl | bash` and live template registries are unavailable (NFR-S1, architecture Stack table).

## What ships in the package

| Component | Source | Network at runtime |
|---|---|---|
| **Seed templates** | `pyforge.marshal.seed.templates` (packaged beside the manifest) | None — read from the installed wheel/conda artifact |
| **Manifest** | `templates/manifest.yaml` (bundled) | None |
| **Copier engine** | Conda dependency `copier>=9.17,<10` | None — conda-provisioned, never pip-installed at runtime |
| **Template render** | `seed/engine/copier.py` via Copier's public API only (FR-120) | None — Genesis wraps `run_copy` / `run_update` against the in-package tree |

There is no secondary download step: installing `pyforge-marshal` (and its conda run-dependencies) is the full bootstrap for the seed machinery.

## What Genesis does not install

**Referenced** manifest entries (`bmad-loop`, `bmad-method`, `pixi`, `tmux`, …) are verified for presence and floor only — Genesis never installs them. In air-gapped sites, pre-stage those packages in the same conda channel/mirror you use for `pyforge-marshal`, then run:

```bash
marshal seed check --repo-root . --strict
```

Referenced-dependency gaps surface as `referenced-dep-missing` (**DRIFT**, or **HARD** with `--strict`). Where available, `doctor check` delegates richer probes; otherwise Genesis uses a minimal local probe.

## Recommended air-gap workflow

1. Mirror the conda channel(s) declared in your pixi/conda environment (including `copier`, `bmad-loop`, and other referenced floors).
2. Install `pyforge-marshal` from the mirror into the target environment.
3. Run `marshal seed adopt` or `init` as in the [adoption guide](adoption-guide.md).
4. Wire `marshal seed check --strict` into offline CI using the same mirrored environment.

## Proof in this repo

Story 12.3 meta-tests (`tests/meta/test_ad65_no_network_stack_imports.py`, `test_ad65_default_template_never_remote.py`) assert the seed layer does not import network stacks and that the default template path is never remote. Re-run after upgrades:

```bash
pixi run -e pyforge-marshal pyforge-marshal-test
```
