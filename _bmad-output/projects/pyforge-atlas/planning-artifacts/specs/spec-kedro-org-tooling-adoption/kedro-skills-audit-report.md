# kedro-skills audit report — `catalog-config`

Story: `12-1-kedro-skills-audit-then-adopt` (fulfills Capability 1 of
`spec-kedro-org-tooling-adoption/SPEC.md`).

**Tool audited:** `kedro-skills==0.1.1` (pinned exactly; `[feature.pyforge-atlas.pypi-dependencies]`
in `pixi.toml`).

**Command run:** `pixi run kedro-skills-audit` (`kedro skills list`, `cwd =
src/shared/packages/pyforge-atlas`) — registry contains exactly one skill:

```
ID                   Category     Status         Description
catalog-config       data         not installed  Kedro catalog configuration guidance for conf/**/*...
```

No growth beyond the single `catalog-config` skill that motivated this story.

**Install command run:** `pixi run kedro-skills-install` (`kedro skills install
catalog-config --ide claude`) — real output: `.claude/skills/catalog-config/SKILL.md`,
`.agents/skills/catalog-config/SKILL.md` (identical canonical copy),
`.agents/skills/.installed.json` (per-file SHA-256 state), and a new
`AGENTS.md` (unconditional `agents_md` block, independent of `--ide`).

**Ground truth audited against:** `src/shared/packages/pyforge-atlas/conf/base/catalog.yml`
(the real catalog) and the enforced `tests/catalog/*` gate. Live run:

```
pixi run --environment pyforge-atlas kedro-catalog-check
...............................................                          [100%]
47 passed in 3.96s
```

**47 passed** — cite this number, not the "38" figure carried by the epic-level
`spec-kedro-org-tooling-adoption/SPEC.md` ("the `kedro-catalog-check=38` invariant")
or any other prior doc; that figure is stale as of this audit (2026-08-09).

---

## Verdicts, by `catalog-config/SKILL.md` section

### 1. "Dataset type naming" — **MIXED (PASS + CONTRADICTS)**

- Module-path convention (`kedro_datasets.<library>.<Type>Dataset`, short form
  also accepted) and the "wrong module" (`kedro.extras.datasets.*` deprecated)
  and "wrong casing" (lowercase `Dataset` since kedro-datasets 2.0, e.g.
  `CSVDataset` not `CSVDataSet`) guidance: **PASS**. `catalog.yml` already uses
  exclusively the short module form with lowercase-`Dataset` casing — e.g.
  `type: api.APIDataset` (`conf/base/catalog.yml:41`), `type:
  pandas.ParquetDataset` (`conf/base/catalog.yml:94`). No enforced test governs
  this specifically, but nothing in the live catalog or in `tests/catalog/*`
  contradicts it.
- "Top-level `layer:` deprecated... Use `metadata.kedro-viz.layer` instead"
  (nested example shown, `SKILL.md:24-33`): **CONTRADICTS**
  `test_every_entry_carries_a_layer_tag`
  (`tests/catalog/test_conventions.py:30-36`). That test reads
  `(spec.get("metadata") or {}).get("layer")` — a **direct, unnested** key —
  and every real catalog entry uses that unnested form, e.g.
  ```
  core_repodata_raw:
    type: api.APIDataset
    url: ...
    metadata:
      layer: raw
  ```
  (`conf/base/catalog.yml:40-44`). Following the guidance's nested
  `metadata.kedro-viz.layer` form would make `spec.get("metadata").get("layer")`
  return `None` for that entry, which is not in `LAYERS`
  (`tests/catalog/conftest.py:58`) — the gate would fail. **Corrected in the
  Atlas override** appended to both installed `SKILL.md` copies.

### 2. "Check the docs before writing an entry" — **PASS**

Doc-verification workflow (report interpreter + version together, verify
dataset type exists via the kedro-datasets docs URL before writing an entry,
never guess from training data). No enforced test governs agent research
behavior; nothing in `tests/catalog/*` or `conf/base/catalog.yml` contradicts
it. Reinforces AD-11's "no inline IO / verify before writing" spirit.

### 3. "Dependencies" (extras naming, e.g. `kedro-datasets[pandas-csvdataset]`) — **PASS**

Not exercised in this repo today — `pyproject.toml` pins bare
`"kedro-datasets>=9.5.0"` with no extras
(`src/shared/packages/pyforge-atlas/pyproject.toml:23`), because the conda-side
`kedro-datasets` run-dep installs the full feature set rather than per-type
pip extras. No enforced test requires or forbids the extras-scoped form, so
this is dormant-but-not-contradicted guidance — correct if this project ever
switches to per-type extras.

### 4. "load_args and save_args" — **PASS**

Generic Kedro capability (pass options through to the underlying library);
no enforced test governs it; not contradicted anywhere in `catalog.yml` (e.g.
entries such as the GitHub GraphQL `load_args.json.query` usage,
`conf/base/catalog.yml:465-468`, already rely on the same mechanism).

### 5. "Factory patterns" — **PASS**

Specificity-ordering guidance (`"{name}"` wildcard entries resolve by
specificity, not file position). No factory-pattern entries exist in
`conf/base/catalog.yml` today (`grep -c '"{' conf/base/catalog.yml` → 0), so
this is dormant guidance — not exercised, but not contradicted by any
`tests/catalog/*` check either.

### 6. "Data directory structure" — **CONTRADICTS**

The guidance's numbered 8-layer table (`data/01_raw/`, `data/02_intermediate/`,
`data/03_primary/`, `data/04_feature/`, `data/05_model_input/`,
`data/06_models/`, `data/07_model_output/`, `data/08_reporting/`,
`SKILL.md:168-181`) contradicts the enforced convention on two axes:

- **Numbering.** `test_output_filepaths_follow_data_layer_name_convention`
  (`tests/catalog/test_conventions.py:39-58`) asserts every persisted output's
  `filepath` starts with `data/{layer}/{name}` — no `NN_` numeric prefix.
  Every real entry confirms the unnumbered form, e.g. `filepath:
  data/intermediate/core_packages_enumerated/core_packages_enumerated.parquet`
  (`conf/base/catalog.yml:95`) and `filepath:
  data/primary/core_downloads/core_downloads.parquet`
  (`conf/base/catalog.yml:116`).
- **Layer set.** `LAYERS = {"raw", "intermediate", "primary", "derived"}`
  (`tests/catalog/conftest.py:58`) is the closed set both
  `test_every_entry_carries_a_layer_tag` and
  `test_output_filepaths_follow_data_layer_name_convention` validate against.
  The guidance's 8-row table introduces four layers this project does not
  have (`feature`, `model_input`, `models`, `model_output`) and renames two
  (`reporting` → this project's closest analog is `derived`); using any of the
  guidance's extra layer names would fail
  `test_every_entry_carries_a_layer_tag` outright (`layer not in LAYERS`).

  **Corrected in the Atlas override** appended to both installed `SKILL.md`
  copies.

### 7. "Credentials" — **PASS**

Reference credentials by key, never inline; credentials live exclusively in
`conf/local/credentials.yml`, gitignored, never in `conf/base/`. This matches
`tests/catalog/test_credential_scoping.py` almost verbatim:
`test_local_credentials_file_is_gitignored`
(`tests/catalog/test_credential_scoping.py:101-113`) asserts
`conf/local/credentials.yml` is `git check-ignore`d, and
`test_no_credential_material_in_tracked_config`
(`tests/catalog/test_credential_scoping.py:116-127`) asserts no
`*credentials*`-named file exists anywhere under tracked `conf/` outside
`conf/local`. Real catalog entries reference credentials exclusively by key,
e.g. `credentials: bigquery_adc` (`conf/base/catalog.yml:201`) and
`credentials: github_token` (`conf/base/catalog.yml:468`) — no inline secret
anywhere in `conf/base/catalog.yml`.

### 8. "OmegaConf interpolation" — **PASS**

`${globals:key}`, `${runtime_params:key}`, `${oc.env:VAR}` interpolation.
Matches this project's own declared convention verbatim: "every external entry
routes through a `${globals:...}` endpoint-base (AD-13) — NO host is ever
hardcoded here" (`conf/base/catalog.yml:15-16`), e.g. `url:
${globals:endpoint_bases.CONDA_FORGE_BASE_URL}/noarch/current_repodata.json`
(`conf/base/catalog.yml:42`).

---

## Summary

| # | Section | Verdict |
|---|---|---|
| 1 | Dataset type naming (module/casing) | PASS |
| 1 | Dataset type naming (`metadata.kedro-viz.layer`) | **CONTRADICTS** `test_every_entry_carries_a_layer_tag` |
| 2 | Check the docs before writing an entry | PASS |
| 3 | Dependencies (extras naming) | PASS (dormant) |
| 4 | load_args and save_args | PASS |
| 5 | Factory patterns | PASS (dormant) |
| 6 | Data directory structure | **CONTRADICTS** `test_output_filepaths_follow_data_layer_name_convention` + `LAYERS` |
| 7 | Credentials | PASS |
| 8 | OmegaConf interpolation | PASS |

Six of eight audited sections pass cleanly (two of those dormant-but-uncontradicted);
two confirmed contradictions, both corrected via an appended "## Atlas overrides"
section at the bottom of **both** installed `SKILL.md` copies
(`src/shared/packages/pyforge-atlas/.claude/skills/catalog-config/SKILL.md` and
`src/shared/packages/pyforge-atlas/.agents/skills/catalog-config/SKILL.md` — the
latter is the canonical copy `AGENTS.md`'s injected block routes every
non-Claude-Code-native reader to).

Adoption outcome: **adopt with corrections** — install proceeds (already done via
`pixi run kedro-skills-install`), guidance is used as-is for the six passing
sections, and the override supersedes the two contradicted sections for every
reader of either installed file.

---

## Drafted upstream issue text (NOT filed — draft only, per the epic SPEC's Never clause)

Two separate issues, drafted here for a human's future explicit go-ahead. No
GitHub issue was created or otherwise filed as part of this story.

### Draft issue 1 — `catalog-config` layer guidance conflicts with Kedro's own unnested `metadata.layer` convention

> **Title:** `catalog-config` skill recommends deprecated/nonexistent nested
> `metadata.kedro-viz.layer`, but modern Kedro-Viz reads unnested `metadata.layer`
>
> **Body:** The `catalog-config` skill's "Dataset type naming" section tells
> agents that top-level `layer:` is deprecated since Kedro 0.19 and to use
> `metadata.kedro-viz.layer` instead — including a worked YAML example. In our
> project (`kedro` >=1.5.0, `kedro-viz` >=12.4.0), Kedro-Viz reads the layer tag
> from the **unnested** `metadata.layer` key, not a `kedro-viz`-namespaced
> sub-key. An agent following this guidance produces catalog entries whose
> layer tag Kedro-Viz silently fails to pick up. Could you confirm which form
> is current for the kedro-datasets/kedro-viz versions this skill targets, and
> update the example if it's stale? Happy to share the exact catalog shape
> that works for us if useful.

### Draft issue 2 — "Data directory structure" table uses the legacy numbered 8-layer scaffold, no mention that project layer sets vary

> **Title:** `catalog-config` "Data directory structure" table hardcodes the
> numbered 8-layer `data/NN_name/` scaffold as *the* convention
>
> **Body:** The skill's "Data directory structure" section presents a single
> fixed table (`data/01_raw/` ... `data/08_reporting/`) as the directory
> convention, with no caveat that this is the `kedro new` starter default
> rather than a Kedro requirement. Our project deliberately uses an unnumbered,
> 4-layer scheme (`data/<layer>/<name>/`, layers `raw`/`intermediate`/`primary`/
> `derived`) enforced by our own test suite — nothing in Kedro itself requires
> the numbered 8-layer form. An agent given this guidance verbatim will
> generate `filepath` values that don't match our project's actual layout.
> Could the guidance note that the directory scaffold is a *starter-template
> convention*, configurable per project, rather than presenting one fixed
> table as universal? Happy to share our project's variant as a second worked
> example if useful.

---

## Notes on tool-managed state (not bugs — do not "fix")

- `.agents/skills/.installed.json` records the SHA-256 of each managed file
  **as installed**, before the "## Atlas overrides" append. This is expected:
  the append is a deliberate, tracked drift against that hash. Verified
  empirically (review loop 1 of this story): running `kedro skills update`
  (no `--force`) after the append refuses and names the modified files,
  preserving the override rather than silently clobbering it — this is the
  tool's own drift-refusal mechanism doing exactly the job the epic SPEC asks
  for ("a version bump re-triggers the audit, not a silent regenerate").
- The `kedro-skills==0.1.1` pin is deliberately exact, with no floor or range.
  If `0.1.1` is ever yanked from PyPI, per the intent-contract's `Block If`
  clause this audit HALTs rather than silently widening the pin to a newer,
  un-audited release.
