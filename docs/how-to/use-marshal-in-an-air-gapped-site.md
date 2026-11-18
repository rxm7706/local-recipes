---
sources:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/engine/copier.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context_bootstrap.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_ad65_no_network_stack_imports.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_ad65_default_template_never_remote.py
  - .github/workflows/substrate-nightly.yml
verified: 2026-11-18
---

# How to use Marshal's seed and substrate bootstrap in an air-gapped site

Use `marshal seed` and `marshal context bootstrap --from` to adopt the operating model and fill a clone's shared substrate where runtime `curl | bash` and live template registries are unavailable (NFR-S1, architecture Stack table).

## When to use this

- You are installing Genesis from a mirrored conda channel.
- You need to know which Marshal paths touch the network, and which never do.
- You are carrying the published substrate pair across an air gap.
- You are rebuilding the substrate with no pair and no network.

:::note
**Prerequisites.** A conda mirror that carries `pyforge-marshal` and its run-dependencies. Mirror setup itself is in [air-gapped mirror setup](air-gapped-mirror-setup.md); the wider enterprise profile is in [enterprise deployment](../explanation/enterprise-deployment.md).
:::

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

Referenced-dependency gaps surface as `referenced-dep-missing` (**DRIFT**, which fails the run under `--strict`). Where available, `doctor check` delegates richer probes; otherwise Genesis uses a minimal local probe.

## Steps

### 1. Mirror the channels

Mirror the conda channel(s) declared in your pixi/conda environment (including `copier`, `bmad-loop`, and other referenced floors).

### 2. Install from the mirror

Install `pyforge-marshal` from the mirror into the target environment.

### 3. Adopt

Run `marshal seed adopt` or `init` as in [How to adopt the operating model in another repository](adopt-the-operating-model-with-marshal-seed.md).

### 4. Wire the offline check

Wire `marshal seed check --strict` into offline CI using the same mirrored environment.

### 5. Carry the substrate across

On a connected host, download the published pair and carry it across; then install it without the network:

```bash
# connected host: the published substrate-nightly assets, built on a CI runner
gh release download substrate-nightly --repo <owner>/<repo> \
  --pattern substrate-manifest.json --pattern substrate.tar.gz --dir substrate-pack
# air-gapped host, after copying substrate-pack/ across
marshal context bootstrap --from substrate-pack
```

Prefer the published pair. Its CI runner has no session transcripts, so its `graph.json` carries none.

:::caution
`marshal context pack --out substrate-pack` on a working checkout ships `graph.json` exactly as that host compiled it. That includes session-transcript nodes and absolute home-directory paths. Use `pack` only when no published pair exists, and review what it carries before it leaves the host.
:::

`context pack` writes deterministic bytes: packing the same substrate twice on one host gives the same archive sha256. A carried copy of the published pair verifies against its own manifest. With no pair and no network, `--offline` rebuilds each member from the checkout, provided the rebuild tools (`codegraph`, and `scribe` with its graph extras) are installed from your mirror.

## The substrate bootstrap: the one explicit fetch (Story 46.1)

`marshal context bootstrap` (also `pyforge context bootstrap`) fills a bare clone with the shared substrate: the structure graph (`.codegraph/codegraph.db`), the planning graph (`.claude/data/pyforge-scribe/graph.json`) and the derived-context distills (`.claude/data/pyforge-scribe/move-list.json`, plus `cocoindex-index.json` when the pack carries it). It is the **second** marshal path that can use the network. The seed machinery above has none. The fetch happens only when you run this verb, and only in its default form:

| Form | Network | What it does |
|---|---|---|
| `marshal context bootstrap` | **Yes**: `gh release download` of the `substrate-nightly` prerelease (`--tag`, `--repo` override) | Announces the fetch on stderr, records `data.source.network: true` in the envelope, then verifies and installs each missing member. `gh` must be authenticated with read access to the repository's releases. |
| `marshal context bootstrap --from <dir>` | **None** | Installs from a pair you already have on disk. |
| `marshal context bootstrap --offline` | **None** | Fetches nothing; rebuilds each missing member locally (`codegraph init -y`, `scribe graph compile --nightly`, `scribe index refresh`). Each rebuild is a named `MRS-CTX-003` finding. |

The fetch shells out to `gh`. Marshal imports no network stack, and `--from` and `--offline` never start `gh`. A member already in the clone is never overwritten. A member that is neither fetched nor rebuilt is `MRS-CTX-004` (exit `1`).

The published pair never carries the planning graph: `.github/workflows/substrate-nightly.yml` builds it only from operator-local surfaces (session transcripts, the gitignored graph store) a GitHub-hosted runner does not have, so it never runs that compiler. That is scribe Epic 8's own HARD boundary, recorded in [How to schedule the Scribe nightly compile](schedule-the-scribe-nightly-compile.md). Every `bootstrap`, even the default networked form, rebuilds the planning graph locally as a named `MRS-CTX-003` finding.

## What the digests prove

`substrate-manifest.json` records a sha256 and a size for every file and for `substrate.tar.gz` itself. Bootstrap checks every one of them before it writes a byte. A mismatch, a malformed manifest or an unsafe archive entry installs nothing: it is reported as `MRS-CTX-005`, and the member falls back to a local rebuild. The digests prove **integrity**, not **authenticity**: the manifest and the archive come from the same release, so anyone who can publish to that release can publish a consistent pair.

## What you get

A repository adopted with no runtime fetch, a conformance check that runs offline, and a clone whose substrate members are each fetched from a carried pair or rebuilt locally with a named finding.

Story 12.3's meta-tests (`test_ad65_no_network_stack_imports.py` and `test_ad65_default_template_never_remote.py` under marshal's `tests/meta/`) assert the seed layer does not import network stacks and that the default template path is never remote. Re-run them after upgrades:

```bash
pixi run -e pyforge-marshal pyforge-marshal-test
```
