"""Story B7 — SbomIntakeDataset + TransitiveResolverDataset + the § 4.10 pure
parsers. Fixture-based, offline (AD-11). Covers AC-1 (resolver offline/resolved/
raise), AC-2 (per-format parse + cfe:*/channel passthrough), AC-4b (NBSP==ASCII)."""

from __future__ import annotations

import json

import pytest
from kedro.io.core import DatasetError

from pyforge.atlas.datasets.sbom_intake import (
    SbomIntakeDataset,
    TransitiveResolverDataset,
    normalize_ws,
    parse_conda_list_text,
    parse_cyclonedx,
    parse_environment_yml,
    parse_intake,
    parse_pip_list_text,
    parse_requirements_txt,
)

NBSP = "\xa0"
NNBSP = " "  # narrow no-break space


# ── AC-4b: NBSP == ASCII ──────────────────────────────────────────────────────


def test_normalize_ws_folds_nbsp_and_narrow_nbsp():
    assert normalize_ws(f"a{NBSP}b{NNBSP}c") == "a b c"


def test_nbsp_pip_list_parses_identically_to_ascii():
    ascii_text = "Package    Version\n-------    -------\nnumpy      1.26.0\nrich       13.7.0\n"
    nbsp_text = ascii_text.replace(" ", NBSP)
    assert parse_pip_list_text(nbsp_text) == parse_pip_list_text(ascii_text)
    # and the content is what we expect
    parsed = parse_pip_list_text(ascii_text)
    assert {(d["name"], d["version"]) for d in parsed} == {("numpy", "1.26.0"), ("rich", "13.7.0")}


def test_nbsp_conda_list_parses_identically_to_ascii():
    ascii_text = (
        "# packages in environment\nnumpy   1.26.0   py311h_0   conda-forge\nrequests 2.31.0  pyhd_0     pypi\n"
    )
    nbsp_text = ascii_text.replace(" ", NBSP)
    assert parse_conda_list_text(nbsp_text) == parse_conda_list_text(ascii_text)
    parsed = parse_conda_list_text(ascii_text)
    by_name = {d["name"]: d for d in parsed}
    assert by_name["numpy"]["ecosystem"] == "conda"
    assert by_name["requests"]["ecosystem"] == "pypi"  # channel == pypi -> pip-installed


# ── AC-2: per-format parse + passthrough preservation ─────────────────────────


def test_parse_requirements_txt():
    deps = parse_requirements_txt("numpy==1.26.0\nrich>=13\n# comment\n-e .\nflask\n")
    assert {(d["name"], d["version"]) for d in deps} == {
        ("numpy", "1.26.0"),
        ("rich", "13"),
        ("flask", None),
    }
    assert all(d["ecosystem"] == "pypi" for d in deps)


def test_parse_environment_yml_with_nested_pip():
    text = "name: env\ndependencies:\n  - python=3.11\n  - numpy\n  - pip:\n    - rich==13.7.0\n"
    deps = parse_environment_yml(text)
    by_name = {d["name"]: d for d in deps}
    assert by_name["numpy"]["ecosystem"] == "conda"
    assert by_name["rich"]["ecosystem"] == "pypi"  # nested pip: block
    assert "python" not in by_name  # python is not a dep row


def test_parse_cyclonedx_preserves_cfe_properties_and_channel_purl():
    doc = {
        "bomFormat": "CycloneDX",
        "components": [
            {
                "name": "numpy",
                "version": "1.26.0",
                "purl": "pkg:conda/numpy@1.26.0?channel=conda-forge",
                "properties": [{"name": "cfe:gap_status", "value": "CURRENT"}],
            }
        ],
    }
    deps = parse_cyclonedx(doc)
    assert deps[0]["purl"] == "pkg:conda/numpy@1.26.0?channel=conda-forge"
    assert deps[0]["properties"] == [{"name": "cfe:gap_status", "value": "CURRENT"}]
    assert deps[0]["ecosystem"] == "conda"


def test_parse_intake_detects_cyclonedx_json_string():
    raw = json.dumps({"bomFormat": "CycloneDX", "components": [{"name": "rich", "version": "13.7.0"}]})
    out = parse_intake(raw, filename="scan.cdx.json")
    assert out["format"] == "cyclonedx"
    assert out["passthrough"] is True
    assert out["deps"][0]["name"] == "rich"


def test_parse_intake_requirements_by_filename():
    out = parse_intake("numpy==1.26.0\n", filename="requirements.txt")
    assert out["format"] == "requirements"
    assert out["deps"][0]["name"] == "numpy"


def test_parse_intake_malformed_sbom_never_crashes():
    """Edge-HIGH: a truncated CycloneDX file resolved by filename must NOT raise
    (json.loads was previously uncaught on the SBOM branch)."""
    out = parse_intake('{"bomFormat":"CycloneDX",', filename="scan.cdx.json")  # truncated JSON
    assert out["format"] == "cyclonedx"
    assert out["deps"] == []
    out2 = parse_intake("{not json", filename="thing.spdx.json")
    assert out2["format"] == "spdx" and out2["deps"] == []


def test_parse_conda_list_explicit_url_rows():
    """Blind LOW-4: `conda list --explicit` URL rows parse to conda deps."""
    text = (
        "@EXPLICIT\n"
        "https://conda.anaconda.org/conda-forge/linux-64/numpy-1.26.0-py311h_0.conda#abc123\n"
        "https://conda.anaconda.org/conda-forge/noarch/rich-13.7.0-pyhd_0.tar.bz2\n"
    )
    deps = parse_conda_list_text(text)
    by_name = {d["name"]: d["version"] for d in deps}
    assert by_name == {"numpy": "1.26.0", "rich": "13.7.0"}
    assert all(d["ecosystem"] == "conda" for d in deps)


# ── SbomIntakeDataset (file IO owner) ─────────────────────────────────────────


def test_sbom_intake_dataset_loads_requirements(tmp_path):
    f = tmp_path / "requirements.txt"
    f.write_text("numpy==1.26.0\nflask\n", encoding="utf-8")
    ds = SbomIntakeDataset(filepath=str(f))
    out = ds.load()
    assert out["format"] == "requirements"
    assert {d["name"] for d in out["deps"]} == {"numpy", "flask"}


def test_sbom_intake_dataset_is_read_only(tmp_path):
    ds = SbomIntakeDataset(filepath=str(tmp_path / "x.txt"))
    with pytest.raises((NotImplementedError, DatasetError), match="read-only"):
        ds.save({})


def test_sbom_intake_loads_pixi_and_pyproject_manifests(tmp_path):
    pixi = tmp_path / "pixi.toml"
    pixi.write_text('[dependencies]\nnumpy = "1.26"\n[pypi-dependencies]\nrich = "13"\n', encoding="utf-8")
    pixi_out = SbomIntakeDataset(filepath=str(pixi)).load()
    assert pixi_out["format"] == "pixi"
    names = {d["name"] for d in pixi_out["deps"]}
    assert names >= {"numpy", "rich"}

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('dependencies = ["flask==3.0.0"]\n', encoding="utf-8")
    py_out = SbomIntakeDataset(filepath=str(pyproject)).load()
    assert py_out["format"] == "pyproject"
    assert any(d["name"] == "flask" for d in py_out["deps"])


def test_sbom_intake_loads_cyclonedx_json_file(tmp_path):
    doc = {
        "bomFormat": "CycloneDX",
        "components": [{"name": "lib", "version": "1.0", "purl": "pkg:conda/lib@1.0"}],
    }
    path = tmp_path / "sbom.cdx.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    out = SbomIntakeDataset(filepath=str(path)).load()
    assert out["format"] == "cyclonedx"
    assert out["passthrough"] is True
    assert out["deps"][0]["purl"].startswith("pkg:conda/")


def test_sbom_intake_loads_conda_and_pip_list_files(tmp_path):
    conda_path = tmp_path / "conda-list.txt"
    conda_path.write_text("numpy 1.0 py311_0 conda-forge\n", encoding="utf-8")
    conda_out = SbomIntakeDataset(filepath=str(conda_path)).load()
    assert conda_out["format"] == "conda-list"
    assert conda_out["deps"][0]["ecosystem"] == "conda"

    pip_path = tmp_path / "pip-list.txt"
    pip_path.write_text('[{"name": "flask", "version": "3.0.0"}]', encoding="utf-8")
    pip_out = SbomIntakeDataset(filepath=str(pip_path)).load()
    assert pip_out["format"] == "pip-list"
    assert pip_out["deps"][0]["name"] == "flask"


def test_sbom_intake_malformed_cyclonedx_returns_empty_deps(tmp_path):
    path = tmp_path / "broken.cdx.json"
    path.write_text("{not-json", encoding="utf-8")
    out = SbomIntakeDataset(filepath=str(path)).load()
    assert out["format"] == "cyclonedx"
    assert out["deps"] == []
    assert out["passthrough"] is True


def test_parse_intake_unknown_filename_falls_back_to_pip_list_heuristic():
    out = parse_intake("Package Version\nnumpy 1.0\n", filename="unknown-manifest.txt")
    assert out["passthrough"] is False
    assert any(d["name"] == "numpy" for d in out["deps"])


def test_sbom_intake_loads_spdx_json_file(tmp_path):
    doc = {
        "SPDXID": "SPDXRef-DOCUMENT",
        "packages": [
            {
                "name": "pkg",
                "versionInfo": "2.0",
                "externalRefs": [{"referenceType": "purl", "referenceLocator": "pkg:pypi/pkg"}],
            }
        ],
    }
    path = tmp_path / "sbom.spdx.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    out = SbomIntakeDataset(filepath=str(path)).load()
    assert out["format"] == "spdx"
    assert out["deps"][0]["name"] == "pkg"


def test_sbom_intake_dataset_loads_requirements_file(tmp_path):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("numpy==1.0\n", encoding="utf-8")
    ds = SbomIntakeDataset(filepath=str(manifest))
    out = ds.load()
    assert out["format"] == "requirements"
    names = {d["name"] for d in out["deps"]}
    assert "numpy" in names


def test_sbom_intake_save_is_read_only(tmp_path):
    ds = SbomIntakeDataset(filepath=str(tmp_path / "x.txt"))
    with pytest.raises(DatasetError, match="read-only"):
        ds.save({})


def test_sbom_intake_dataset_constructs_offline_without_touching_the_file():
    # DataCatalog.from_config instantiation must not do IO (the file may not exist).
    ds = SbomIntakeDataset(filepath="/nonexistent/intake.json")
    assert ds._describe()["filepath"] == "/nonexistent/intake.json"


# ── AC-1: TransitiveResolverDataset (offline / resolved / raise) ──────────────


def test_resolver_offline_returns_unresolved_marker(tmp_path):
    f = tmp_path / "requirements.txt"
    f.write_text("numpy\n", encoding="utf-8")
    ds = TransitiveResolverDataset(filepath=str(f))  # resolver=None == offline
    out = ds.load()
    assert out["resolution"] == "unresolved"
    assert out["deps"] == []
    assert out["depth"] is None


def test_resolver_resolved_records_depth_and_fanout(tmp_path):
    f = tmp_path / "requirements.txt"
    f.write_text("flask\n", encoding="utf-8")

    def stub_resolver(text):
        # a bare `requirements.txt` resolves to a full transitive set
        return {
            "deps": [
                {"name": "flask", "version": "3.0.0", "ecosystem": "pypi", "manifest": "resolved"},
                {"name": "jinja2", "version": "3.1.4", "ecosystem": "pypi", "manifest": "resolved"},
                {"name": "werkzeug", "version": "3.0.3", "ecosystem": "pypi", "manifest": "resolved"},
            ],
            "depth": 2,
            "fanout": 3,
        }

    ds = TransitiveResolverDataset(filepath=str(f), resolver=stub_resolver)
    out = ds.load()
    assert out["resolution"] == "resolved"
    assert out["depth"] == 2
    assert out["fanout"] == 3
    assert {d["name"] for d in out["deps"]} == {"flask", "jinja2", "werkzeug"}


def test_resolver_exception_degrades_to_unresolved_never_crashes(tmp_path):
    f = tmp_path / "requirements.txt"
    f.write_text("numpy\n", encoding="utf-8")

    def broken_resolver(text):
        raise RuntimeError("solver blew up / network down")

    ds = TransitiveResolverDataset(filepath=str(f), resolver=broken_resolver)
    out = ds.load()  # must NOT raise (AD-13)
    assert out["resolution"] == "unresolved"
    assert "resolver failed" in out["reason"]


def test_resolver_missing_file_degrades_to_unresolved(tmp_path):
    # offline consumer profile: a missing manifest never takes the run down
    def stub(text):
        return {"deps": [], "depth": 0, "fanout": 0}

    ds = TransitiveResolverDataset(filepath=str(tmp_path / "nope.txt"), resolver=stub)
    out = ds.load()
    assert out["resolution"] == "unresolved"


def test_resolver_dataset_is_read_only(tmp_path):
    ds = TransitiveResolverDataset(filepath=str(tmp_path / "x.txt"))
    with pytest.raises((NotImplementedError, DatasetError), match="read-only"):
        ds.save({})


def test_requirements_extras_and_url_yield_no_garbage_version():
    """Independent B7 review F1: _REQ_RE is verbatim-faithful to legacy — an
    extras spec or a direct-URL ref must yield version=None, never a garbage
    version that becomes an invalid purl (pkg:pypi/requests@[security]>=2.0)."""
    from pyforge.atlas.datasets.sbom_intake import parse_requirements_txt

    txt = "\n".join(
        [
            "requests[security]>=2.0",
            "uvicorn[standard]",
            "black[d]==23.1.0",
            "foo @ https://example.com/foo.whl",
            "numpy>=1.20,<2.0",
            "plain==1.2.3",
        ]
    )
    deps = {d["name"]: d.get("version") for d in parse_requirements_txt(txt, "requirements.txt")}
    assert deps["requests"] is None  # extras, no valid version captured
    assert deps["uvicorn"] is None
    assert deps["black"] is None  # black[d]==... → extras before operator
    assert deps["foo"] is None  # direct URL ref
    assert deps["numpy"] == "1.20"  # legacy captures the first pin
    assert deps["plain"] == "1.2.3"
    # and no dep carries a version starting with a non-digit
    for v in deps.values():
        assert v is None or v[0].isdigit()
