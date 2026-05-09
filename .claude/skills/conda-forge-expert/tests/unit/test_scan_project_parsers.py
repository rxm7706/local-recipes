"""Unit tests for scan_project's manifest / lock-file / SBOM parsers.

Each parser gets a tiny synthetic fixture (under tests/fixtures/manifest_samples/)
and a focused assertion: was the right number of deps extracted, with the
correct ecosystem tag.

These tests are pure-Python — no network, no external tools. Container /
Helm / kubectl integrations are skipped by the marker mechanism in
test_atlas_clis.py instead.
"""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "manifest_samples"


@pytest.fixture(scope="module")
def sp(load_module):
    """Load scan_project once per module."""
    return load_module("scan_project.py")


# ── Python ecosystem parsers ─────────────────────────────────────────────────

def test_pyproject_toml_pep621_pep735_pdm_hatch(sp):
    deps = sp.parse_pyproject_toml(FIXTURES / "pyproject.toml")
    names = sorted(d.name for d in deps)
    # PEP 621 [project.dependencies]
    assert "requests" in names
    # PEP 621 [project.optional-dependencies]
    assert any(d.manifest.endswith("#extras.dev") for d in deps if d.name == "pytest")
    # PEP 735 [dependency-groups]
    assert any(d.manifest.endswith("#dep-groups.test") for d in deps if d.name == "coverage")
    # include-group resolution: docs group includes test, so coverage shows in both
    docs_coverage = [d for d in deps if d.name == "coverage" and "docs" in d.manifest]
    assert docs_coverage, "include-group should bring `coverage` into `docs` group"
    # PDM dev-dependencies
    assert any(d.manifest.endswith("#pdm.dev.lint") for d in deps if d.name == "mypy")
    # Hatch envs
    assert any(d.manifest.endswith("#hatch.envs.default") for d in deps if d.name == "bandit")


def test_pipfile_lock(sp):
    deps = sp.parse_pipfile_lock(FIXTURES / "Pipfile.lock")
    by_name = {d.name: d for d in deps}
    assert by_name["requests"].version == "2.31.0"  # leading `==` stripped
    assert all(d.ecosystem == "pypi" for d in deps)
    # default + develop sections both captured
    assert any(d.manifest.endswith("#default") for d in deps)
    assert any(d.manifest.endswith("#develop") for d in deps)


def test_pipfile_manifest(sp):
    """Pipfile (no lock) — TOML manifest with [packages]/[dev-packages]."""
    deps = sp.parse_pipfile(FIXTURES / "Pipfile")
    by_name = {d.name: d for d in deps}
    assert "flask" in by_name
    assert "pytest" in by_name
    # Dict-form spec: sqlalchemy = {version = "==2.0.25", extras = ["asyncio"]}
    assert by_name["sqlalchemy"].version == "2.0.25"


# ── npm ecosystem parsers ────────────────────────────────────────────────────

def test_package_lock_v3(sp):
    deps = sp.parse_package_lock_json(FIXTURES / "package-lock.json")
    names = {d.name for d in deps}
    assert {"lodash", "express"} <= names
    # Scoped package: @types/node
    assert any("@types/node" == d.name for d in deps)
    assert all(d.ecosystem == "npm" for d in deps)


def test_yarn_lock_v1(sp):
    deps = sp.parse_yarn_lock(FIXTURES / "yarn.lock")
    names = {d.name for d in deps}
    assert "lodash" in names
    assert "@types/react" in names
    assert all(d.ecosystem == "npm" for d in deps)


def test_pnpm_lock(sp):
    deps = sp.parse_pnpm_lock(FIXTURES / "pnpm-lock.yaml")
    by_name = {d.name: d for d in deps}
    # Peer-dep marker `(react-dom@18.2.0)` must be stripped from version
    assert by_name["react"].version == "18.2.0"
    assert "@types/node" in by_name
    assert all(d.ecosystem == "npm" for d in deps)


# ── Go ecosystem parsers ─────────────────────────────────────────────────────

def test_go_mod(sp):
    deps = sp.parse_go_mod(FIXTURES / "go.mod")
    names = {d.name for d in deps}
    assert "github.com/gorilla/mux" in names
    assert all(d.ecosystem == "golang" for d in deps)


# ── Ruby / PHP / conda-lock ──────────────────────────────────────────────────

def test_gemfile_lock(sp):
    deps = sp.parse_gemfile_lock(FIXTURES / "Gemfile.lock")
    by_name = {d.name: d for d in deps}
    assert by_name["rails"].version == "7.1.2"
    # Sub-dep lines (indent=6) should be skipped — only top-level specs
    assert all(d.ecosystem == "gem" for d in deps)


def test_composer_lock(sp):
    deps = sp.parse_composer_lock(FIXTURES / "composer.lock")
    by_name = {d.name: d for d in deps}
    assert "symfony/console" in by_name
    assert "phpunit/phpunit" in by_name
    assert all(d.ecosystem == "composer" for d in deps)


def test_conda_lock(sp):
    deps = sp.parse_conda_lock(FIXTURES / "conda-lock.yml")
    # Manager-aware: numpy via conda manager → conda; requests via pip → pypi
    by_name = {(d.name, d.ecosystem): d for d in deps}
    assert ("numpy", "conda") in by_name
    assert ("requests", "pypi") in by_name


# ── SBOM parsers ─────────────────────────────────────────────────────────────

def test_sbom_cyclonedx_xml(sp):
    deps = sp.parse_sbom_cyclonedx_xml(FIXTURES / "bom.xml")
    by_name = {d.name: d for d in deps}
    assert by_name["numpy"].ecosystem == "pypi"
    assert by_name["numpy"].version == "2.0.0"


def test_sbom_spdx_tagvalue(sp):
    deps = sp.parse_sbom_spdx_tagvalue(FIXTURES / "sbom.spdx")
    by_name = {d.name: d for d in deps}
    assert by_name["openssl"].ecosystem == "apt"  # purl pkg:deb/...
    assert by_name["jinja2"].ecosystem == "pypi"


def test_sbom_spdx_3(sp):
    deps = sp.parse_sbom_spdx_3(FIXTURES / "sbom.spdx3.json")
    by_name = {d.name: d for d in deps}
    assert by_name["numpy"].ecosystem == "pypi"
    assert by_name["requests"].version == "2.31.0"


def test_syft_json(sp):
    deps = sp.parse_syft_json(FIXTURES / "syft.json")
    by_eco = {d.ecosystem for d in deps}
    # syft type-to-eco map: deb→apt, python→pypi, go-module→golang
    assert by_eco >= {"apt", "pypi", "golang"}


def test_trivy_json(sp):
    deps = sp.parse_trivy_json(FIXTURES / "trivy.json")
    by_eco = {d.ecosystem for d in deps}
    # trivy Type-to-eco map: debian→apt, pip→pypi
    assert by_eco >= {"apt", "pypi"}


def test_sbom_relationships_cyclonedx(sp):
    rels = sp.parse_sbom_relationships(FIXTURES / "bom_with_rels.json")
    # Synthetic file has app→[lib1, lib2] + lib1→[lib2]
    assert "app@1.0" in rels
    assert "lib2@3.0" in rels["app@1.0"]


def test_vex_cyclonedx(sp):
    vex = sp.parse_vex_cyclonedx(FIXTURES / "vex_test.json")
    # Single component bom-ref → single VEX statement
    assert vex
    statement = list(vex.values())[0][0]
    assert statement["state"] == "not_affected"
    assert statement["cve_id"] == "CVE-2099-9999"


# ── Container / GitOps parsers ───────────────────────────────────────────────

def test_kubernetes_manifest(sp):
    deps = sp.parse_kubernetes_manifest(FIXTURES / "k8s" / "deployment.yaml")
    images = {d.name for d in deps}
    # Multi-doc: Deployment + CronJob both produce image refs
    assert "alpine" in images
    assert "nginx" in images or "nvcr.io/nvidia/pytorch" in images
    assert all(d.ecosystem == "oci-image" for d in deps)


def test_helm_values(sp):
    deps = sp.parse_helm_values(FIXTURES / "helm" / "values.yaml")
    # String-form `image:` and structured {repository, tag, registry}
    images = {d.extras.get("image_ref") for d in deps}
    assert any("nginx" in i for i in images if i)
    assert all(d.ecosystem == "oci-image" for d in deps)


def test_dockerfile_multistage(sp):
    deps, base_images = sp.parse_containerfile(FIXTURES / "Dockerfile.multistage")
    # FROM lines + COPY --from=alpine:3.19 (external image)
    assert "golang:1.21" in base_images
    assert "alpine:3.19" in base_images  # external COPY --from


# ── Tag normalization ────────────────────────────────────────────────────────

def test_normalize_release_tag(sp, load_module):
    """The conda_forge_atlas tag normalizer (used by Phase K)."""
    cfa = load_module("conda_forge_atlas.py")
    assert cfa._normalize_release_tag("v3.0.44") == "3.0.44"
    assert cfa._normalize_release_tag("Release_1_6_15") == "1_6_15"
    assert cfa._normalize_release_tag("RELEASE-2.0") == "2.0"
    assert cfa._normalize_release_tag(None) is None
    assert cfa._normalize_release_tag("") is None


# ── Docker image-ref splitting (ecosystem='oci-image') ───────────────────────

def test_dep_purl_oci_image(sp):
    """`Dep.purl()` for OCI images falls through to 'generic' since there's
    no standard purl type for OCI references; the original ref is preserved
    in extras['image_ref']."""
    d = sp.Dep(name="nginx", version="1.25", ecosystem="oci-image", manifest="k8s",
               extras={"image_ref": "nginx:1.25"})
    purl = d.purl()
    # 'oci-image' isn't in the known set, so falls back to 'generic'
    assert purl == "pkg:generic/nginx@1.25"
    assert d.extras["image_ref"] == "nginx:1.25"
