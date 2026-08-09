# kedro-skills v0.1.1 audit — `catalog-config` guidance vs Atlas AD-invariants

Story 12.1 (kedro-skills audit-then-adopt), Capability 1 of
`spec-kedro-org-tooling-adoption`. Audits every subsection of the
`kedro-skills==0.1.1` `catalog-config` skill's generated guidance against
the enforced conventions in
`src/shared/packages/pyforge-atlas/tests/catalog/*` (the `kedro-catalog-check`
gate, 38 checks across 6 files). Findings are evidence-backed with
file:line citations from both the test suite (the enforced contract) and
the live `conf/base/catalog.yml` / `globals.yml` (proof the contract is
actively exercised, not just declared).

## Verification of ground truth (live, not cached)

- `pixi run kedro-skills-audit` (`kedro skills list`, run from
  `src/shared/packages/pyforge-atlas`) resolved and installed
  `kedro-skills==0.1.1` from PyPI and printed exactly **one** registry
  entry: `catalog-config` (category `data`, status `not installed`,
  description `Kedro catalog configuration guidance for conf/**/*...`).
  Confirms the spec's investigation claim — the registry has not grown
  beyond `catalog-config` since the Dream was captured.
- The installed package's guidance source is
  `<pixi env>/lib/python3.14/site-packages/kedro_skills/skills/catalog-config/SKILL.md`
  (203 lines) — read directly, not paraphrased from the spec.
- The installed package ships renderers for exactly: `agents_md`, `claude`,
  `copilot`, `cursor` (`kedro_skills/renderers/`) — confirms `--ide claude`
  only touches the Claude surface; no vscode-specific renderer exists to
  accidentally invoke.

## Subsection-by-subsection verdicts

### `## Dataset type naming`

- **Use the current module path / short-form resolution** — **PASS**.
  Every one of the catalog's 86 entries uses current module paths or
  Kedro's built-in short forms (`pandas.ParquetDataset`, `api.APIDataset`,
  `pyforge.atlas.datasets.IncrementalParquetDataset`, ...;
  `conf/base/catalog.yml:102,108,115,168,180` for examples). All 86
  materialize successfully offline in
  `tests/catalog/test_catalog_resolution.py::test_full_catalog_materializes_with_stub_credentials_offline`
  (test_catalog_resolution.py:74-91) and individually in
  `test_every_entry_instantiates_individually` (test_catalog_resolution.py:94-111)
  — a bogus/legacy type path would fail construction there.
- **"Wrong module": `kedro.extras.datasets.*` is deprecated** — **PASS**.
  Zero occurrences of `kedro.extras.datasets` anywhere in
  `conf/base/catalog.yml` (verified by grep); reinforced by the same
  materialization gate above.
- **"Wrong casing": lowercase `Dataset` (e.g. `CSVDataset` not
  `CSVDataSet`)** — **PASS**. Every type in the live catalog uses the
  post-2.0 lowercase-`Dataset` casing (`ParquetDataset`, `APIDataset`,
  `IncrementalParquetDataset`, `MappingCacheDataset`, `VDBStoreDataset`,
  `OSVOfflineStoreDataset`, `BasiliskBatchDataset` — `catalog.yml:102-370`).
- **"Top-level `layer:` is deprecated ... use `metadata.kedro-viz.layer`
  instead"** — **CONTRADICTS-`test_every_entry_carries_a_layer_tag`**.
  Atlas's enforced convention is the UNNESTED `metadata.layer` key
  (`tests/catalog/test_conventions.py:30-36`):

  ```python
  def test_every_entry_carries_a_layer_tag(catalog_config):
      bad = {}
      for name, spec in catalog_config.items():
          layer = (spec.get("metadata") or {}).get("layer")
          if layer not in LAYERS:
              bad[name] = layer
      assert not bad, f"missing/invalid metadata.layer: {bad}"
  ```

  `(spec.get("metadata") or {}).get("layer")` reads `metadata.layer`
  directly — a nested `metadata.kedro-viz.layer` key (the guidance's
  recommendation) resolves to `None` there, which is not in `LAYERS`
  (`conftest.py:58`) and would FAIL this test. All 86 live entries already
  use the unnested form, e.g. `conf/base/catalog.yml:42-44`:

  ```yaml
  core_repodata_raw:
    type: api.APIDataset
    url: ${globals:endpoint_bases.CONDA_FORGE_BASE_URL}/noarch/current_repodata.json
    metadata:
      layer: raw
  ```

  Confirmed: this is a genuine contradiction, not a stale spec claim.

### `## Check the docs before writing an entry`

**PASS** (compatible; no enforced test targets *process*, but nothing
contradicts it). The mandated doc-verification-before-writing workflow
(confirm interpreter, verify installed `kedro-datasets` version, fetch the
docs page, refuse to guess) is reinforced in spirit by
`tests/catalog/test_catalog_resolution.py`'s materialize-every-entry gate:
an undocumented/nonexistent dataset type or constructor argument would fail
construction there, which is exactly the failure mode this workflow exists
to prevent upstream of the gate.

### `## Dependencies`

**PASS**. The `kedro-datasets[<module>-<class>]` extras-naming convention
(lowercase, hyphen-joined module+class) is external to `conf/**/*.yml` and
touches no AD-invariant in `tests/catalog/*`; no contradiction found.

### `## load_args and save_args`

**PASS**. No test in `tests/catalog/*` constrains `load_args`/`save_args`
usage, and the guidance (read documented constructor args, don't guess)
doesn't conflict with anything enforced. Not currently exercised by any
live catalog entry (no entry uses `load_args`/`save_args` today), so this
is an unexercised-but-uncontradicted PASS.

### `## Factory patterns`

**PASS**. The specificity-ordering claim ("resolution order is by
specificity, not file position ... fewest wildcards, longest literal
prefix") matches Kedro's own dataset-factory resolution and is not
contradicted by any test in `tests/catalog/*`. Not currently exercised —
the live catalog has zero `"{name}"`-style factory entries (verified by
grep for `^"{` across `conf/base/catalog.yml`: no matches) — so this is
also an unexercised-but-uncontradicted PASS, not a verified-in-production
one.

### `## Data directory structure`

**CONTRADICTS-`test_output_filepaths_follow_data_layer_name_convention`**.
The guidance's numbered 8-layer table (`data/01_raw/`, `data/02_intermediate/`,
`data/03_primary/`, `data/04_feature/`, `data/05_model_input/`,
`data/06_models/`, `data/07_model_output/`, `data/08_reporting/`) does not
match Atlas's enforced scheme: unnumbered `data/<layer>/<dataset_name>/`
with exactly four layers, `LAYERS = {"raw", "intermediate", "primary",
"derived"}` (`tests/catalog/conftest.py:58-59`). Enforced by
`tests/catalog/test_conventions.py:39-58`:

```python
def test_output_filepaths_follow_data_layer_name_convention(catalog_config):
    ...
    for name, spec in catalog_config.items():
        layer = (spec.get("metadata") or {}).get("layer")
        path = spec.get("filepath") or spec.get("path")
        ...
        if layer in OUTPUT_LAYERS or is_local_data:
            prefix = f"data/{layer}/{name}"
            if not (path == prefix or path.startswith(prefix + "/")):
                bad[name] = path
    assert not bad, f"filepath convention violations: {bad}"
```

A filepath following the guidance's table (e.g. `data/01_raw/companies.csv`)
would fail this check on two counts: the numbered `01_raw` segment doesn't
match Atlas's bare `raw`, and the path doesn't include the dataset name as
its own directory segment. The live catalog already follows the enforced
convention, e.g. `conf/base/catalog.yml:100-102`:

```yaml
core_packages_enumerated:
  type: pandas.ParquetDataset
  filepath: data/intermediate/core_packages_enumerated/core_packages_enumerated.parquet
```

Also note: the guidance's layer *names* (Raw/Intermediate/Primary/Feature/
Model input/Models/Model output/Reporting, 8 total) don't even 1:1 map onto
Atlas's 4 (`raw`, `intermediate`, `primary`, `derived`) — this is a
structural mismatch, not just a numbering-prefix cosmetic difference.
Confirmed: this is a genuine contradiction, not a stale spec claim.

### `## Credentials`

**PASS** — matches `tests/catalog/test_credential_scoping.py` almost
verbatim.

- "Reference credentials by key — do not inline secrets" matches
  `test_credentials_attach_only_where_the_host_requires_them`
  (test_credential_scoping.py:45-48): the credentialed-entry set is exactly
  the per-host `CREDENTIAL_ALLOWLIST`, i.e. `credentials: <key>` references
  only, never inline secret material.
- "The key must match an entry in `conf/local/credentials.yml` ... Never
  create or edit credential files under `conf/base/` ... Credentials belong
  exclusively in `conf/local/credentials.yml`, which is gitignored" matches
  two tests directly:
  - `test_local_credentials_file_is_gitignored`
    (test_credential_scoping.py:101-113) — asserts
    `conf/local/credentials.yml` is git-ignore-matched via
    `git check-ignore`.
  - `test_no_credential_material_in_tracked_config`
    (test_credential_scoping.py:116-127) — asserts no `*credentials*`-named
    file exists anywhere under tracked `conf/` outside `conf/local`.

### `## OmegaConf interpolation`

**PASS**. The `${globals:key}` / `${runtime_params:key}` / `${oc.env:VAR}`
interpolation forms the guidance describes are exactly how Atlas's catalog
resolves every external host, e.g. `conf/base/catalog.yml:42`:

```yaml
url: ${globals:endpoint_bases.CONDA_FORGE_BASE_URL}/noarch/current_repodata.json
```

`globals.yml`'s header (`conf/base/globals.yml:1-10`) documents the same
pattern: "Catalog entries reference these via `${globals:...}` and NEVER
hardcode a host." The 20-override-point + 31-total-surface accounting is
gate-checked in `tests/catalog/test_override_points.py:36-59`
(`test_override_points_are_19_live_plus_1_reserved`,
`test_total_env_override_surface_is_pinned`), which exercises the same
`env_or`-resolver-backed interpolation the guidance describes.

## Summary

| Subsection | Verdict |
|---|---|
| Dataset type naming — module path / short form | PASS |
| Dataset type naming — wrong-module warning | PASS |
| Dataset type naming — wrong-casing warning | PASS |
| Dataset type naming — `metadata.kedro-viz.layer` | **CONTRADICTS**-`test_every_entry_carries_a_layer_tag` |
| Check the docs before writing an entry | PASS |
| Dependencies (extras naming) | PASS |
| load_args and save_args | PASS |
| Factory patterns | PASS |
| Data directory structure (numbered 8-layer table) | **CONTRADICTS**-`test_output_filepaths_follow_data_layer_name_convention` |
| Credentials | PASS |
| OmegaConf interpolation | PASS |

Two confirmed contradictions, both re-verified live against the current
tree (not merely inherited from the spec's prior investigation). Every
other subsection passes or is compatible/unexercised-but-uncontradicted.
No subsection was left unaudited.

## Disposition

Adoption proceeds per the Spec's "audit-then-adopt" contract: since the
guidance substantially passes, `kedro skills install catalog-config --ide
claude` is run for real from the project root, and the two confirmed
contradictions are recorded as an appended "## Atlas overrides" section at
the bottom of the installed
`src/shared/packages/pyforge-atlas/.claude/skills/catalog-config/SKILL.md`
(never edited inline — matches the repo's existing CFE-comment-at-bottom
convention) rather than silently dropped or silently kept. See that file's
bottom section for the enforced corrections agents must follow instead.

## Draft upstream-issue text (NOT filed — draft only, per the Spec's Never clause)

Two issues would be worth raising with `kedro-org/kedro-skills` if a human
approves filing them. Drafted here for that future decision; **no live
GitHub issue has been opened**.

---

**Draft issue 1 — `catalog-config`: "layer:" migration guidance recommends
a key Kedro-Viz does not read**

> The `catalog-config` skill's "Dataset type naming" section says the
> top-level `layer:` key is deprecated since Kedro 0.19 and instructs
> replacing it with `metadata.kedro-viz.layer`. Cross-checking against
> Kedro-Viz's own metadata-parsing convention (and our own project's
> `metadata.layer`, unnested, working correctly with `kedro viz run`), the
> nested `metadata.kedro-viz.layer` form does not appear to be what
> current Kedro-Viz reads for the layer tag — the unnested `metadata.layer`
> is. Suggest verifying the nesting against a real `kedro viz run` render
> before shipping this guidance, since it currently instructs users toward
> a key that (in our testing) Kedro-Viz doesn't pick up.

---

**Draft issue 2 — `catalog-config`: "Data directory structure" hardcodes
the create-kedro-project 8-layer numbered scaffold as if it were a Kedro
convention**

> The "Data directory structure" table presents the numbered 8-layer
> `data/01_raw/` ... `data/08_reporting/` scheme as *the* directory
> convention. This is actually just the default scaffold from
> `kedro new` / the data-engineering starter — Kedro itself has no
> enforced numbering or layer-count requirement (any project is free to
> define its own layer set and path convention, as ours does with an
> unnumbered 4-layer `data/<layer>/<dataset_name>/` scheme). Suggest
> softening the table to "a common convention is..." rather than
> presenting it as the only correct layout, since it can lead an
> AI-authored catalog entry to fight a project's own established
> convention instead of following it.

---

*Audit performed 2026-08-09, `kedro-skills==0.1.1` (PyPI, exact pin),
against `src/shared/packages/pyforge-atlas/tests/catalog/*` as of commit
`c09088a6e6e3ae6ab8d9923dcb7df61a18052fa0` (this story's baseline
revision).*
