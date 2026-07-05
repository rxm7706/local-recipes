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


# ── S5a intake parsers (cyclonedx-universe-inventory Wave C) ─────────────────

def test_pdm_lock(sp):
    deps = sp.parse_pdm_lock(FIXTURES / "pdm.lock")
    by_name = {d.name: d for d in deps}
    assert by_name["requests"].version == "2.31.0"
    # names lowercased (PDM preserves upstream casing in the lock)
    assert "charset-normalizer" in by_name
    assert all(d.ecosystem == "pypi" for d in deps)


def test_pylock_toml_pep751(sp):
    """PEP 751 uses the PLURAL [[packages]] key — the parser must not read
    the uv/poetry/pdm singular [[package]] shape."""
    deps = sp.parse_pylock_toml(FIXTURES / "pylock.toml")
    by_name = {d.name: d for d in deps}
    assert by_name["attrs"].version == "25.3.0"
    assert by_name["ruamel.yaml"].version == "0.18.10"  # dots preserved


def test_pip_list_columns(sp):
    deps = sp.parse_pip_text(FIXTURES / "pip-list.txt")
    by_name = {d.name: d for d in deps}
    # header + dashes rows skipped, columnar rows parsed
    assert by_name["numpy"].version == "1.26.4"
    assert by_name["typing_extensions"].version == "4.12.2"
    assert "package" not in by_name
    assert all(d.ecosystem == "pypi" for d in deps)


def test_pip_freeze(sp):
    deps = sp.parse_pip_text(FIXTURES / "pip-freeze.txt")
    by_name = {d.name: d for d in deps}
    assert by_name["certifi"].version == "2024.2.2"
    # env-marker suffix stripped
    assert by_name["requests"].version == "2.31.0"
    # direct ref: no version, url captured
    assert by_name["mypkg"].version is None
    assert by_name["mypkg"].extras["url"].startswith("file:///")
    # editable install resolved via #egg=
    assert by_name["devtool"].extras.get("editable") is True
    # option lines (--extra-index-url) are not deps
    assert not any(d.name.startswith("--") for d in deps)


def test_pip_list_json(sp, tmp_path):
    p = tmp_path / "pip.json"
    p.write_text('[{"name": "Flask", "version": "3.0.2"}, {"name": "idna", "version": "3.7"}]')
    deps = sp.parse_pip_text(p)
    by_name = {d.name: d for d in deps}
    assert by_name["flask"].version == "3.0.2"


def test_conda_list_default(sp):
    deps = sp.parse_conda_list_text(FIXTURES / "conda-list.txt")
    by_name = {d.name: d for d in deps}
    assert by_name["numpy"].version == "1.26.4"
    assert by_name["numpy"].ecosystem == "conda"
    # pip-installed rows (channel `pypi`) are tagged ecosystem=pypi
    assert by_name["sphinx"].ecosystem == "pypi"
    # header/comment rows skipped
    assert "name" not in by_name


def test_conda_list_export(sp):
    deps = sp.parse_conda_list_text(FIXTURES / "conda-list-export.txt")
    by_name = {d.name: d for d in deps}
    assert by_name["python"].version == "3.12.3"
    assert by_name["ruamel.yaml"].version == "0.18.6"
    assert by_name["libffi"].extras["build"] == "h7f98852_5"


def test_conda_list_explicit(sp):
    deps = sp.parse_conda_list_text(FIXTURES / "conda-list-explicit.txt")
    by_name = {d.name: d for d in deps}
    # URL basename parsed name-version-build; @EXPLICIT marker skipped
    assert by_name["_openmp_mutex"].version == "4.5"
    assert by_name["numpy"].version == "1.26.4"
    assert by_name["tzdata"].version == "2024a"
    # `--explicit --md5` / conda-lock renders append #<hash> — must still parse
    assert by_name["zstd"].version == "1.5.6"


def test_conda_list_json(sp, tmp_path):
    p = tmp_path / "conda.json"
    p.write_text(
        '[{"base_url": "https://conda.anaconda.org/conda-forge", '
        '"channel": "conda-forge", "dist_name": "numpy-1.26.4-py312_0", '
        '"name": "numpy", "version": "1.26.4"}, '
        '{"base_url": null, "channel": "pypi", "dist_name": "sphinx-7.3.7", '
        '"name": "sphinx", "version": "7.3.7"}]'
    )
    deps = sp.parse_conda_list_text(p)
    by_name = {d.name: d for d in deps}
    assert by_name["numpy"].ecosystem == "conda"
    assert by_name["sphinx"].ecosystem == "pypi"


def test_meta_yaml_manifest(sp):
    deps = sp.parse_meta_yaml(FIXTURES / "meta.yaml")
    by_key = {(d.name, d.manifest): d for d in deps}
    # host + run sections captured with section labels
    assert ("pip", "meta.yaml#host") in by_key
    assert ("numpy", "meta.yaml#run") in by_key
    # jinja-templated names ({{ compiler('c') }}) are skipped
    assert not any("compiler" in d.name for d in deps)
    # jinja inside a constraint keeps the name, drops the version
    py = by_key[("python", "meta.yaml#host")]
    assert py.version is None
    # exact pins: conda `name 1.2.3` and `name ==1.2.3` forms
    assert by_key[("click", "meta.yaml#run")].version == "8.1.7"
    assert by_key[("pyyaml", "meta.yaml#run")].version == "6.0.1"
    # range constraint → no exact version, constraint preserved
    numpy = by_key[("numpy", "meta.yaml#run")]
    assert numpy.version is None and numpy.extras["constraint"] == ">=1.22"
    # selector comment stripped
    assert ("typing-extensions", "meta.yaml#run") in by_key
    # plain trailing comment stripped — never becomes a constraint
    req = by_key[("requests", "meta.yaml#run")]
    assert req.extras.get("constraint") is None
    # run_constrained entries are NOT hard run deps
    assert not any(d.name in ("dask", "mpich") for d in deps)
    # test.requires is NOT a requirements block
    assert not any(d.name == "pytest" for d in deps)
    assert all(d.ecosystem == "conda" for d in deps)


def test_recipe_entry_conda_fuzzy_not_exact(sp):
    # `=1.22` is conda fuzzy (1.22.*) — a range, never an exact pin
    name, version, constraint = sp._parse_recipe_entry("numpy =1.22")
    assert name == "numpy" and version is None and constraint == "=1.22"
    # `==` and bare remain exact
    assert sp._parse_recipe_entry("numpy ==1.22")[1] == "1.22"
    assert sp._parse_recipe_entry("numpy 1.22")[1] == "1.22"


def test_recipe_yaml_dict_section_inert(sp, tmp_path):
    p = tmp_path / "recipe.yaml"
    p.write_text(
        "package: {name: bad, version: '1.0'}\n"
        "requirements:\n"
        "  run: {python: '>=3.9', numpy: '>=1.22'}\n"
    )
    assert sp.parse_recipe_yaml(p) == []


def test_requirements_range_bound_records_operator(sp, tmp_path):
    p = tmp_path / "requirements.txt"
    p.write_text("requests>=2.0\nflask==3.0.2\nweird!=1.2\n")
    by_name = {d.name: d for d in sp.parse_requirements_txt(p)}
    assert by_name["requests"].extras["op"] == ">="
    assert "op" not in by_name["flask"].extras       # == is a real pin
    assert by_name["weird"].extras["op"] == "!="


def test_recipe_yaml_manifest(sp):
    deps = sp.parse_recipe_yaml(FIXTURES / "recipe.yaml")
    by_key = {(d.name, d.manifest): d for d in deps}
    assert ("hatchling", "recipe.yaml#host") in by_key
    # ${{ }} in constraint → name kept, version dropped
    assert by_key[("python", "recipe.yaml#host")].version is None
    # bare version = exact pin
    assert by_key[("rich", "recipe.yaml#run")].version == "13.7.1"
    # if/then/else conditionals: both branches collected
    assert ("colorama", "recipe.yaml#run") in by_key
    assert ("uvloop", "recipe.yaml#run") in by_key
    # per-output requirements labeled by output name
    assert by_key[("httpx", "recipe.yaml#demo-suite-extra#run")].version == "0.27.0"
    # templated names (${{ pin_subpackage(...) }}) skipped
    assert not any("pin_subpackage" in d.name for d in deps)
