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
    ascii_text = "# packages in environment\nnumpy   1.26.0   py311h_0   conda-forge\nrequests 2.31.0  pyhd_0     pypi\n"
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
    ds = SbomIntakeDataset(filepath=str(f), allowed_root=str(tmp_path))
    out = ds.load()
    assert out["format"] == "requirements"
    assert {d["name"] for d in out["deps"]} == {"numpy", "flask"}


def test_sbom_intake_dataset_is_read_only(tmp_path):
    ds = SbomIntakeDataset(filepath=str(tmp_path / "x.txt"))
    with pytest.raises((NotImplementedError, DatasetError), match="read-only"):
        ds.save({})


def test_sbom_intake_dataset_constructs_offline_without_touching_the_file():
    # DataCatalog.from_config instantiation must not do IO (the file may not exist).
    ds = SbomIntakeDataset(filepath="/nonexistent/intake.json")
    assert ds._describe()["filepath"] == "/nonexistent/intake.json"


def test_sbom_intake_rejects_oversized_file(tmp_path, monkeypatch):
    # AUD-ATLAS-038: hard size cap before parse.
    f = tmp_path / "big.txt"
    f.write_text("x" * 64, encoding="utf-8")
    monkeypatch.setattr(
        "pyforge.atlas.datasets.sbom_intake._MAX_INTAKE_BYTES", 16
    )
    ds = SbomIntakeDataset(filepath=str(f), allowed_root=str(tmp_path))
    with pytest.raises(DatasetError, match="size cap"):
        ds.load()


def test_resolver_rejects_oversized_file(tmp_path, monkeypatch):
    f = tmp_path / "big.txt"
    f.write_text("x" * 64, encoding="utf-8")
    monkeypatch.setattr(
        "pyforge.atlas.datasets.sbom_intake._MAX_INTAKE_BYTES", 16
    )

    def stub(text):
        raise AssertionError("resolver must not run on oversized intake")

    ds = TransitiveResolverDataset(
        filepath=str(f), resolver=stub, allowed_root=str(tmp_path)
    )
    with pytest.raises(DatasetError, match="size cap"):
        ds.load()


# ── AC-1: TransitiveResolverDataset (offline / resolved / raise) ──────────────


def test_resolver_offline_returns_unresolved_marker(tmp_path):
    f = tmp_path / "requirements.txt"
    f.write_text("numpy\n", encoding="utf-8")
    ds = TransitiveResolverDataset(filepath=str(f), allowed_root=str(tmp_path))  # resolver=None == offline
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

    ds = TransitiveResolverDataset(
        filepath=str(f), resolver=stub_resolver, allowed_root=str(tmp_path)
    )
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

    ds = TransitiveResolverDataset(
        filepath=str(f), resolver=broken_resolver, allowed_root=str(tmp_path)
    )
    out = ds.load()  # must NOT raise (AD-13)
    assert out["resolution"] == "unresolved"
    assert "resolver failed" in out["reason"]


def test_resolver_missing_file_degrades_to_unresolved(tmp_path):
    # offline consumer profile: a missing manifest never takes the run down
    def stub(text):
        return {"deps": [], "depth": 0, "fanout": 0}

    ds = TransitiveResolverDataset(
        filepath=str(tmp_path / "nope.txt"), resolver=stub, allowed_root=str(tmp_path)
    )
    out = ds.load()
    assert out["resolution"] == "unresolved"


def test_resolver_path_escape_raises_dataset_error(tmp_path):
    # AUD-ATLAS-016 + 025: escape is a policy failure, not AD-13 offline.
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("should-not-read\n", encoding="utf-8")
    allowed = tmp_path / "allowed"
    allowed.mkdir()

    def stub(text):
        raise AssertionError("resolver must not run on escaped path")

    ds = TransitiveResolverDataset(
        filepath=str(secret), resolver=stub, allowed_root=str(allowed)
    )
    with pytest.raises(DatasetError, match="must lie under"):
        ds.load()


def test_resolver_dataset_is_read_only(tmp_path):
    ds = TransitiveResolverDataset(filepath=str(tmp_path / "x.txt"))
    with pytest.raises((NotImplementedError, DatasetError), match="read-only"):
        ds.save({})


def test_requirements_extras_and_url_yield_no_garbage_version():
    """Independent B7 review F1: _REQ_RE is verbatim-faithful to legacy — an
    extras spec or a direct-URL ref must yield version=None, never a garbage
    version that becomes an invalid purl (pkg:pypi/requests@[security]>=2.0)."""
    from pyforge.atlas.datasets.sbom_intake import parse_requirements_txt
    txt = "\n".join([
        "requests[security]>=2.0",
        "uvicorn[standard]",
        "black[d]==23.1.0",
        "foo @ https://example.com/foo.whl",
        "numpy>=1.20,<2.0",
        "plain==1.2.3",
    ])
    deps = {d["name"]: d.get("version") for d in parse_requirements_txt(txt, "requirements.txt")}
    assert deps["requests"] is None          # extras, no valid version captured
    assert deps["uvicorn"] is None
    assert deps["black"] is None             # black[d]==... → extras before operator
    assert deps["foo"] is None               # direct URL ref
    assert deps["numpy"] == "1.20"           # legacy captures the first pin
    assert deps["plain"] == "1.2.3"
    # and no dep carries a version starting with a non-digit
    for v in deps.values():
        assert v is None or v[0].isdigit()
