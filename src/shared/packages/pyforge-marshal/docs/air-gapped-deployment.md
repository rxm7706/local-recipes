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

## The substrate bootstrap: the one explicit fetch (Story 46.1)

`marshal context bootstrap` (also `pyforge context bootstrap`) fills a bare clone with the shared
substrate: the structure graph (`.codegraph/codegraph.db`), the planning graph
(`.claude/data/pyforge-scribe/graph.json`) and the derived-context distills
(`.claude/data/pyforge-scribe/move-list.json`, plus `cocoindex-index.json` when the pack carries
it). It is the **second** marshal path that can use the network. The seed machinery above has
none. The fetch happens only when you run this verb, and only in its default form:

| Form | Network | What it does |
|---|---|---|
| `marshal context bootstrap` | **Yes**: `gh release download` of the `substrate-nightly` prerelease (`--tag`, `--repo` override) | Announces the fetch on stderr before it starts, records `data.source.network: true` in the envelope, then verifies and installs each missing member |
| `marshal context bootstrap --from <dir>` | **None** | Installs from a pair you already have on disk |
| `marshal context bootstrap --offline` | **None** | Fetches nothing; rebuilds each missing member locally (`codegraph init -y`, `scribe graph compile --nightly`, `scribe index refresh`), and each rebuild is a named `MRS-CTX-003` finding |

The fetch shells out to `gh`. Marshal imports no network stack, and `--from` and `--offline` never
start `gh`. A member already in the clone is never overwritten. A member that is neither fetched
nor rebuilt is `MRS-CTX-004` (exit `1`).

**What the digests prove.** `substrate-manifest.json` records a sha256 and a size for every file
and for `substrate.tar.gz` itself. Bootstrap checks every one of them before it writes a byte. A
mismatch, a malformed manifest or an unsafe archive entry installs nothing: it is reported as
`MRS-CTX-005`, and the member falls back to a local rebuild. The digests prove **integrity**, not
**authenticity**: the manifest and the archive come from the same release, so anyone who can
publish to that release can publish a consistent pair.

**Air-gapped sites.** On a connected host, produce the pair and carry it across; then install it
without the network:

```bash
# connected host (or download the substrate-nightly assets there)
marshal context pack --out substrate-pack
# air-gapped host, after copying substrate-pack/ across
marshal context bootstrap --from substrate-pack
```

`context pack` writes deterministic bytes: packing the same substrate twice gives the same archive
sha256, so the pair you carry can be compared against the published one. With no pair and no
network, `--offline` rebuilds each member from the checkout, provided the rebuild tools
(`codegraph`, and `scribe` with its graph extras) are installed from your mirror.
