"""Unit tests — the identity API + ``SourceContract`` adapters (Story 7.1).

Covers: PEP-503/alias/conda identity resolution (AC2), both shipped
adapters' happy paths and every tolerant-skip edge case, both adapters'
``SourceContract`` conformance (AC1), and the registry mechanism including
AC3's extensibility proof with a stub third adapter.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import textwrap
from pathlib import Path

import pytest

from pyforge.warden import sources as sources_module
from pyforge.warden.models import Ecosystem
from pyforge.warden.sources import (
    CycloneDXSourceAdapter,
    ManifestSourceAdapter,
    PackageIdentity,
    SourceContract,
    SourceEvidence,
    register_source,
    registered_sources,
    resolve_identity,
    source_factories,
)


def _write_cyclonedx(tmp_path: Path, document: object, filename: str = "sbom.json") -> Path:
    path = tmp_path / filename
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


# --- resolve_identity / PackageIdentity (AC2) --------------------------------


def test_pep503_variants_resolve_to_the_same_identity():
    a = resolve_identity(Ecosystem.PYPI, "scikit_learn", "1.3.0")
    b = resolve_identity(Ecosystem.PYPI, "Scikit-Learn", "1.3.0")
    assert a == b
    assert a.canonical_name == "scikit-learn"


def test_curated_alias_resolves_to_the_same_identity_as_pep503_variants():
    aliased = resolve_identity(Ecosystem.PYPI, "sklearn", "1.3.0")
    canonical = resolve_identity(Ecosystem.PYPI, "scikit-learn", "1.3.0")
    assert aliased == canonical


def test_ac2_three_raw_names_yield_the_same_package_identity():
    variants = {
        resolve_identity(Ecosystem.PYPI, "scikit_learn", "1.3.0"),
        resolve_identity(Ecosystem.PYPI, "Scikit-Learn", "1.3.0"),
        resolve_identity(Ecosystem.PYPI, "sklearn", "1.3.0"),
    }
    assert len(variants) == 1


def test_conda_name_left_verbatim_no_alias_lookup():
    identity = resolve_identity(Ecosystem.CONDA, "typing_extensions", None)
    assert identity == PackageIdentity(
        ecosystem=Ecosystem.CONDA,
        canonical_name="typing_extensions",
        version=None,
        purl="pkg:conda/typing_extensions",
    )


def test_conda_alias_table_is_never_consulted():
    # "sklearn" is a pypi-only alias key; a conda package literally named
    # "sklearn" must never be silently rewritten to "scikit-learn".
    identity = resolve_identity(Ecosystem.CONDA, "sklearn", "1.3.0")
    assert identity.canonical_name == "sklearn"


def test_empty_string_version_normalizes_to_none():
    identity = resolve_identity(Ecosystem.PYPI, "requests", "")
    assert identity.version is None


def test_purl_is_derived_from_the_alias_resolved_canonical_name():
    identity = resolve_identity(Ecosystem.PYPI, "sklearn", "1.3.0")
    assert identity.purl == "pkg:pypi/scikit-learn@1.3.0"


def test_package_identity_is_frozen():
    identity = resolve_identity(Ecosystem.PYPI, "requests", "2.31.0")
    with pytest.raises(dataclasses.FrozenInstanceError):
        identity.version = "9.9.9"  # type: ignore[misc]


def test_source_evidence_is_frozen():
    identity = resolve_identity(Ecosystem.PYPI, "requests", "2.31.0")
    evidence = SourceEvidence(identity=identity, source_name="test", locator="loc", raw_name="requests")
    with pytest.raises(dataclasses.FrozenInstanceError):
        evidence.raw_name = "other"  # type: ignore[misc]


# --- CycloneDXSourceAdapter ---------------------------------------------------


def test_cyclonedx_adapter_happy_path_every_evidence_field(tmp_path):
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "components": [
            {
                "type": "library",
                "name": "requests",
                "version": "2.31.0",
                "purl": "pkg:pypi/requests@2.31.0",
            },
            {
                "type": "library",
                "name": "typing_extensions",
                "version": "4.9.0",
                "purl": "pkg:conda/typing_extensions@4.9.0",
            },
        ],
    }
    path = _write_cyclonedx(tmp_path, document)

    evidence = CycloneDXSourceAdapter(path).ingest()

    assert evidence == (
        SourceEvidence(
            identity=resolve_identity(Ecosystem.PYPI, "requests", "2.31.0"),
            source_name="cyclonedx",
            locator=str(path),
            raw_name="requests",
        ),
        SourceEvidence(
            identity=resolve_identity(Ecosystem.CONDA, "typing_extensions", "4.9.0"),
            source_name="cyclonedx",
            locator=str(path),
            raw_name="typing_extensions",
        ),
    )


def test_cyclonedx_adapter_missing_document_degrades_to_empty(tmp_path):
    adapter = CycloneDXSourceAdapter(tmp_path / "does-not-exist.json")
    assert adapter.fetch() is None
    assert adapter.ingest() == ()


@pytest.mark.parametrize(
    "raw_text",
    [
        "not json at all {{{",
        json.dumps([1, 2, 3]),  # top-level not an object
        json.dumps({"specVersion": "1.6", "components": []}),  # missing bomFormat
        json.dumps({"bomFormat": "SPDX", "components": []}),  # wrong bomFormat
        json.dumps({"bomFormat": "CycloneDX"}),  # missing components
        json.dumps({"bomFormat": "CycloneDX", "components": "nope"}),  # not a list
    ],
)
def test_cyclonedx_adapter_malformed_doc_validation_fails(tmp_path, raw_text):
    path = tmp_path / "sbom.json"
    path.write_text(raw_text, encoding="utf-8")
    adapter = CycloneDXSourceAdapter(path)
    assert adapter.validate(adapter.parse(adapter.fetch())) is None
    assert adapter.ingest() == ()


def test_cyclonedx_adapter_component_missing_purl_is_skipped(tmp_path):
    document = {
        "bomFormat": "CycloneDX",
        "components": [
            {"name": "no-purl-pkg", "version": "1.0.0"},
            {"name": "empty-purl-pkg", "version": "1.0.0", "purl": ""},
            {
                "name": "requests",
                "version": "2.31.0",
                "purl": "pkg:pypi/requests@2.31.0",
            },
        ],
    }
    path = _write_cyclonedx(tmp_path, document)
    evidence = CycloneDXSourceAdapter(path).ingest()
    assert [e.raw_name for e in evidence] == ["requests"]


def test_cyclonedx_adapter_unparseable_purl_string_is_skipped_not_raised(tmp_path):
    document = {
        "bomFormat": "CycloneDX",
        "components": [
            {"name": "bad", "purl": "not-a-purl"},
            {
                "name": "requests",
                "version": "2.31.0",
                "purl": "pkg:pypi/requests@2.31.0",
            },
        ],
    }
    path = _write_cyclonedx(tmp_path, document)
    evidence = CycloneDXSourceAdapter(path).ingest()
    assert [e.raw_name for e in evidence] == ["requests"]


def test_cyclonedx_adapter_unrecognized_purl_type_is_skipped(tmp_path):
    document = {
        "bomFormat": "CycloneDX",
        "components": [
            {"name": "leftpad", "purl": "pkg:npm/leftpad@1.0.0"},
            {
                "name": "requests",
                "version": "2.31.0",
                "purl": "pkg:pypi/requests@2.31.0",
            },
        ],
    }
    path = _write_cyclonedx(tmp_path, document)
    evidence = CycloneDXSourceAdapter(path).ingest()
    assert [e.raw_name for e in evidence] == ["requests"]


def test_cyclonedx_adapter_missing_name_falls_back_to_purl_name(tmp_path):
    document = {
        "bomFormat": "CycloneDX",
        "components": [{"version": "2.31.0", "purl": "pkg:pypi/requests@2.31.0"}],
    }
    path = _write_cyclonedx(tmp_path, document)
    evidence = CycloneDXSourceAdapter(path).ingest()
    assert len(evidence) == 1
    assert evidence[0].raw_name == "requests"


def test_cyclonedx_adapter_versionless_purl_resolves_to_none_version(tmp_path):
    document = {
        "bomFormat": "CycloneDX",
        "components": [{"name": "requests", "purl": "pkg:pypi/requests"}],
    }
    path = _write_cyclonedx(tmp_path, document)
    evidence = CycloneDXSourceAdapter(path).ingest()
    assert len(evidence) == 1
    assert evidence[0].identity.version is None


# --- ManifestSourceAdapter -----------------------------------------------


def test_manifest_adapter_happy_path_every_evidence_field(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = ["Requests==2.31.0"]\n',
        encoding="utf-8",
    )

    evidence = ManifestSourceAdapter(tmp_path).ingest()

    assert evidence == (
        SourceEvidence(
            identity=resolve_identity(Ecosystem.PYPI, "Requests", "2.31.0"),
            source_name="manifest",
            locator=str(tmp_path),
            raw_name="Requests",
        ),
    )


def test_manifest_adapter_skips_malformed_manifest_keeps_valid_one(tmp_path):
    good_dir = tmp_path / "good"
    good_dir.mkdir()
    (good_dir / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["requests==2.31.0"]\n',
        encoding="utf-8",
    )
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    (bad_dir / "pyproject.toml").write_text("[project\ndependencies = [", encoding="utf-8")

    evidence = ManifestSourceAdapter(tmp_path).ingest()

    assert len(evidence) == 1
    assert evidence[0].raw_name == "requests"


def test_manifest_adapter_unreadable_target_degrades_to_empty_tuple(tmp_path):
    missing = tmp_path / "does-not-exist"
    assert ManifestSourceAdapter(missing).ingest() == ()


def test_manifest_adapter_empty_target_yields_empty_tuple(tmp_path):
    assert ManifestSourceAdapter(tmp_path).ingest() == ()


def test_manifest_adapter_conda_ecosystem_manifest(tmp_path):
    """Parity with the CycloneDX adapter's own tests, which already cover
    both ecosystems -- this adapter's happy-path test above only exercises
    pypi (``pyproject.toml``); an ``environment.yml`` proves the conda
    path too."""
    (tmp_path / "environment.yml").write_text(
        "name: demo\ndependencies:\n  - typing_extensions==4.9.0\n",
        encoding="utf-8",
    )

    evidence = ManifestSourceAdapter(tmp_path).ingest()

    assert len(evidence) == 1
    assert evidence[0].identity.ecosystem is Ecosystem.CONDA
    assert evidence[0].identity.canonical_name == "typing_extensions"


def test_manifest_adapter_alias_resolves_end_to_end_through_ingest(tmp_path):
    """The ``_PYPI_ALIASES`` table applied inside ``resolve_identity``
    flows all the way through ``ManifestSourceAdapter.ingest()``, not just
    through a direct ``resolve_identity`` call."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["sklearn==1.3.0"]\n',
        encoding="utf-8",
    )

    evidence = ManifestSourceAdapter(tmp_path).ingest()

    assert len(evidence) == 1
    assert evidence[0].identity.canonical_name == "scikit-learn"


# --- SourceContract conformance (AC1) ----------------------------------------


def test_cyclonedx_adapter_conforms_to_source_contract(tmp_path):
    assert isinstance(CycloneDXSourceAdapter(tmp_path / "sbom.json"), SourceContract)


def test_manifest_adapter_conforms_to_source_contract(tmp_path):
    assert isinstance(ManifestSourceAdapter(tmp_path), SourceContract)


def test_ac1_heterogeneous_sources_yield_evidence_through_identical_interface(
    tmp_path,
):
    cyclonedx_path = _write_cyclonedx(
        tmp_path,
        {
            "bomFormat": "CycloneDX",
            "components": [
                {
                    "name": "requests",
                    "version": "2.31.0",
                    "purl": "pkg:pypi/requests@2.31.0",
                }
            ],
        },
    )
    manifest_dir = tmp_path / "project"
    manifest_dir.mkdir()
    (manifest_dir / "pyproject.toml").write_text(
        '[project]\nname = "demo"\ndependencies = ["packaging==24.0"]\n',
        encoding="utf-8",
    )

    cyclonedx_adapter: SourceContract = CycloneDXSourceAdapter(cyclonedx_path)
    manifest_adapter: SourceContract = ManifestSourceAdapter(manifest_dir)

    cyclonedx_evidence = cyclonedx_adapter.ingest()
    manifest_evidence = manifest_adapter.ingest()

    assert all(isinstance(e, SourceEvidence) for e in cyclonedx_evidence)
    assert all(isinstance(e, SourceEvidence) for e in manifest_evidence)
    assert cyclonedx_evidence[0].identity.canonical_name == "requests"
    assert manifest_evidence[0].identity.canonical_name == "packaging"


# --- registry (isolated via monkeypatch — see docstring) ---------------------


def _snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources_module, "_SOURCE_FACTORIES", [*sources_module._SOURCE_FACTORIES])


class _StubSource:
    name = "stub"

    def fetch(self) -> object:
        return None

    def parse(self, raw: object) -> object:
        return None

    def validate(self, parsed: object) -> object:
        return None

    def ingest(self) -> tuple[SourceEvidence, ...]:
        return ()


def test_registry_starts_empty(monkeypatch):
    _snapshot(monkeypatch)
    assert source_factories() == ()
    assert registered_sources() == ()


def test_register_source_appends_in_deterministic_order(monkeypatch):
    _snapshot(monkeypatch)

    class StubOne(_StubSource):
        name = "stub-one"

    class StubTwo(_StubSource):
        name = "stub-two"

    returned = register_source(StubOne)
    assert returned is StubOne  # decorator-friendly
    register_source(StubTwo)

    names = [source.name for source in registered_sources()]
    assert names == ["stub-one", "stub-two"]


def test_register_source_is_idempotent_for_the_same_factory(monkeypatch):
    _snapshot(monkeypatch)
    register_source(_StubSource)
    before = len(source_factories())
    register_source(_StubSource)
    assert len(source_factories()) == before


def test_registered_sources_returns_fresh_instances(monkeypatch):
    _snapshot(monkeypatch)
    register_source(_StubSource)
    first = registered_sources()
    second = registered_sources()
    assert first[-1] is not second[-1]


def test_third_adapter_registers_without_touching_existing_adapters(monkeypatch):
    """AC3: a later adapter (e.g. an Artifactory adapter) implements
    ``SourceContract`` and calls ``register_source`` with no change to the
    two shipped adapters, ``resolve_identity``, or any other part of this
    module."""
    _snapshot(monkeypatch)

    class StubArtifactorySource(_StubSource):
        name = "stub-artifactory"

    register_source(StubArtifactorySource)

    assert isinstance(StubArtifactorySource(), SourceContract)
    names = [source.name for source in registered_sources()]
    assert "stub-artifactory" in names


def _code_without_docstrings(obj: object) -> str:
    """``obj``'s source with every docstring (an ``Expr`` whose value is a
    string constant) stripped -- so a structural reference check inspects
    actual CODE coupling only, never an explanatory cross-reference in
    prose (this codebase's docstrings routinely name sibling
    classes/modules -- e.g. ``ManifestSourceAdapter.fetch``'s own docstring
    names ``CycloneDXSourceAdapter`` purely to explain the mirrored
    contract, not to depend on it)."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(obj)))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def test_shipped_adapters_do_not_reference_each_other():
    """AC3, structurally verified: the two shipped adapters do not
    reference each other."""
    cyclonedx_source = _code_without_docstrings(CycloneDXSourceAdapter)
    manifest_source = _code_without_docstrings(ManifestSourceAdapter)
    assert "ManifestSourceAdapter" not in cyclonedx_source
    assert "CycloneDXSourceAdapter" not in manifest_source


def test_registry_has_no_adapter_specific_branching():
    """AC3, structurally verified: the registry has no adapter-specific
    branching."""
    registry_source = "".join(
        inspect.getsource(func) for func in (register_source, source_factories, registered_sources)
    )
    assert "CycloneDXSourceAdapter" not in registry_source
    assert "ManifestSourceAdapter" not in registry_source
