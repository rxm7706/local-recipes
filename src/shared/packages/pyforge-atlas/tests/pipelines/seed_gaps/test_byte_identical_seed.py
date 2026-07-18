"""THE HEADLINE (Story B6, AC-2): byte-identical-seed guarantee as a pipeline test.

Write the three fixture seed files (a small ``lts-registry.yaml``,
``cwe_categories_seed.json``, ``spdx.schema.json`` with an ``enum``) into a tmp
dir, build a kedro ``DataCatalog`` whose ``seed_*`` datasets point at them
(real ``YAMLDataset`` / ``JSONDataset``, mirroring conf/base/catalog.yml) +
``MemoryDataset``s for the cross-pipeline inputs and the four report outputs,
hash each seed file (sha256), run the FULL ``seed_gaps`` pipeline through
``SequentialRunner``, re-hash, and assert byte-identical AND that the four
report outputs were produced. The suggesters only PROPOSE — they never mutate
the curated seeds (git review decides); the guarantee is by construction (pure
nodes receive already-loaded data) and proven end-to-end here.
"""

from __future__ import annotations

import hashlib
import json

import pandas as pd
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner
from kedro_datasets.json import JSONDataset
from kedro_datasets.yaml import YAMLDataset

from pyforge.atlas.pipelines.seed_gaps import create_pipeline

_LTS_YAML = """\
version: 1
updated: 2026-07-06
products:
  django:
    slug: django
    aliases: [Django]
    source: endoflife
    lts_policy: true
    added: 2026-07-06
"""

_CWE_SEED = {
    "_doc": {"purpose": "fixture seed — human-readable metadata, not data"},
    "CWE-89": "Injection",
}

_SPDX_SCHEMA = {
    "$comment": "fixture",
    "type": "string",
    "enum": ["MIT", "Apache-2.0", "BSD-3-Clause"],
}

_SEED_REPORTS = (
    "seed_gaps_lts_registry_report",
    "seed_gaps_cwe_report",
    "seed_gaps_spdx_report",
    "seed_gaps_license_map_report",
)


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_catalog(tmp_path):
    """Real YAMLDataset/JSONDataset over the on-disk fixture seeds + in-memory
    cross-pipeline inputs and report outputs — mirrors the catalog wiring."""
    lts_path = tmp_path / "lts-registry.yaml"
    cwe_path = tmp_path / "cwe_categories_seed.json"
    spdx_path = tmp_path / "spdx.schema.json"
    # Write the seed files ONCE, as the authoritative curated bytes.
    lts_path.write_text(_LTS_YAML, encoding="utf-8")
    cwe_path.write_text(json.dumps(_CWE_SEED, indent=2), encoding="utf-8")
    spdx_path.write_text(json.dumps(_SPDX_SCHEMA, indent=2), encoding="utf-8")

    catalog = DataCatalog()
    # seed datasets — read-only, on-disk (exactly the catalog dataset types).
    catalog["seed_lts_registry"] = YAMLDataset(filepath=str(lts_path))
    catalog["seed_cwe_categories"] = JSONDataset(filepath=str(cwe_path))
    catalog["seed_spdx_schema"] = JSONDataset(filepath=str(spdx_path))

    # cross-pipeline inputs (rebuild-produced) as MemoryDatasets.
    catalog["seed_spdx_upstream_list_raw"] = MemoryDataset(
        {"licenses": [{"licenseId": "MIT"}, {"licenseId": "GPL-2.0-only"}]}
    )
    catalog["pypi_endoflife_raw"] = MemoryDataset(["django", "numpy", "foo"])
    catalog["core_packages_enumerated"] = MemoryDataset(
        pd.DataFrame(
            {
                "conda_name": ["numpy", "python-foo", "django"],
                "conda_license": ["BSD-3-Clause", "GPL-2.0-only", "MIT"],
            }
        )
    )
    catalog["pypi_conda_mapping"] = MemoryDataset(
        pd.DataFrame(
            {
                "pypi_name": ["numpy"],
                "conda_name": ["numpy"],
                "match_source": ["g10_spelling"],
            }
        )
    )
    catalog["vulnerability_cwe_categories"] = MemoryDataset(
        pd.DataFrame(
            {
                "cwe_id": ["CWE-22", "CWE-89"],
                "cwe_name": ["Path Traversal", "SQL Injection"],
                "category": ["Other", "Other"],
            }
        )
    )
    catalog["pypi_intelligence_enriched"] = MemoryDataset(
        pd.DataFrame(
            {
                "license_spdx": [None, "MIT"],
                "license_raw": ["the mit license", "MIT"],
            }
        )
    )
    # report outputs as MemoryDatasets (the derived ParquetDatasets in prod).
    for name in _SEED_REPORTS:
        catalog[name] = MemoryDataset()

    return catalog, {"lts": lts_path, "cwe": cwe_path, "spdx": spdx_path}


def test_seed_files_are_byte_identical_before_and_after_a_full_run(tmp_path):
    catalog, seeds = _build_catalog(tmp_path)
    before = {k: _sha256(p) for k, p in seeds.items()}

    SequentialRunner().run(create_pipeline(), catalog)

    after = {k: _sha256(p) for k, p in seeds.items()}
    assert after == before, "a seed file changed during the seed_gaps run"

    # the four report outputs were produced (materialized in the catalog).
    for name in _SEED_REPORTS:
        out = catalog[name].load()
        assert isinstance(out, pd.DataFrame)


def test_no_seed_gaps_node_writes_a_seed_dataset():
    """Structural reinforcement: no node lists any ``seed_*`` dataset as an
    output — a seed write path cannot exist (the byte-identical guarantee is by
    construction, the run above proves it end-to-end)."""
    pipeline = create_pipeline()
    for n in pipeline.nodes:
        seed_outputs = {o for o in n.outputs if o.startswith("seed_")}
        # the report OUTPUTS are `seed_gaps_*_report`; the curated SEED inputs
        # are `seed_lts_registry` / `seed_cwe_categories` / `seed_spdx_schema` /
        # `seed_spdx_upstream_list_raw` — none may be an output.
        assert not (seed_outputs & set(pipeline.inputs())), n.name
    # no curated seed input is written by ANY node.
    seed_inputs = {
        "seed_lts_registry",
        "seed_cwe_categories",
        "seed_spdx_schema",
        "seed_spdx_upstream_list_raw",
    }
    assert not (pipeline.outputs() & seed_inputs)
