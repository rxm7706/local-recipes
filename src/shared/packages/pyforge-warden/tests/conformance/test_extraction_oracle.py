"""The differential-oracle — ``RecipeV1Extractor``/``MetaV0Extractor`` vs.
``rattler_build``/``conda_build``'s real renderers (Story 2.2, ratcheted by
Story 2.3's complex-construct fixtures).

``py-rattler-build``/``conda-build`` are TEST-ONLY dependencies
(``pixi.toml``'s ``[feature.pyforge-warden.dependencies]`` — never a
``pyforge-warden`` runtime dependency). Unlike ``test_lockfile_oracle.py``'s
HARD-FAIL convention (``py-rattler`` was already provisioned everywhere
that suite runs), this oracle SKIPS when either renderer is unimportable —
an explicit divergence recorded in the spec's Boundaries, because these two
renderers aren't guaranteed provisioned the way ``py-rattler`` already was.

Assertion is NAME-LEVEL coverage only (``extracted-names ⊇
rendered-names``) — never version equality: the renderer variant-pins bare
deps we correctly leave unversioned (confirmed live: bare ``python``
rendered ``python 3.14.*`` under conda_build's own variant config). The
common-case fixtures are fully resolvable (no unrecognized Jinja
construct), so every extracted component in THOSE two tests lands
``PARSED``; the "modulo NAME_ONLY/UNION_MARKED" allowance is exercised by
the two ``_complex`` tests below (Story 2.3), whose fixtures deliberately
exercise ``compiler()``/``stdlib()`` build-tool exclude, ``pin_subpackage()``
intra-recipe exclude, and the selector-union construct (v1 ``if``/``then``/
``else``, v0 ``# [cond]`` sibling entries) — live-verified against the real
renderers (see each test's own inline variant-config comment) before being
wired in here.

``environment.yml``/``pixi.toml`` get NO oracle here (Boundaries): neither
format has a template/render step, so ``safe_load``/``tomllib`` parsing IS
the ground truth (the same no-oracle precedent as ``extract/pyproject.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.warden.discovery import META_YAML_KIND, RECIPE_YAML_KIND
from pyforge.warden.extract.meta_v0 import MetaV0Extractor
from pyforge.warden.extract.recipe_v1 import RecipeV1Extractor
from pyforge.warden.models import ScannedManifest
from pyforge.warden.routing import DefaultRouter

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "projects"
RECIPE_FIXTURE = FIXTURES / "recipe_common" / "recipe.yaml"
META_FIXTURE = FIXTURES / "meta_common" / "meta.yaml"
RECIPE_COMPLEX_FIXTURE = FIXTURES / "recipe_complex" / "recipe.yaml"
META_COMPLEX_FIXTURE = FIXTURES / "meta_complex" / "meta.yaml"

# compiler()/stdlib() resolve to REAL build-tool matchspecs under a variant
# config (live-verified: `gcc_linux-64 12.*`/`sysroot_linux-64 2.17.*` under
# rattler_build; `gcc_linux-64 14.*`/`sysroot_linux-64 2.17.*` under
# conda_build's own different default variant, same LEADING-TOKEN names) --
# excluded from the rendered-comparison set on BOTH sides, the same
# treatment `run_constraints`' "scipy" already gets in the common-case
# oracle above, since extraction deliberately excludes what these two
# constructs render to (never a Component).
_BUILD_TOOL_RENDERED_NAMES = {"gcc_linux-64", "sysroot_linux-64"}
# pin_subpackage(...) renders to a STRUCTURED (non-string) dict entry under
# rattler_build (filtered by the isinstance(str) check below) but a PLAIN
# STRING "mypkg-core" under conda_build (needs an explicit name exclusion,
# since the string-filter can't catch it) -- both live-verified.
_PIN_SUBPACKAGE_RENDERED_NAME = "mypkg-core"


def _rattler_build_module():
    try:
        import rattler_build
    except ImportError:
        pytest.skip(
            "py-rattler-build is not importable -- it is a test-only "
            "oracle dependency (pixi.toml's "
            "[feature.pyforge-warden.dependencies]); 2.2 explicitly "
            "SKIPS (never hard-fails) when a renderer isn't provisioned "
            "(Boundaries: divergence from 2.6's py-rattler hard-fail "
            "convention). Run this suite via "
            "`pixi run -e pyforge-warden pyforge-warden-test`."
        )
    return rattler_build


def _conda_build_module():
    try:
        from conda_build import api
    except ImportError:
        pytest.skip(
            "conda-build is not importable -- it is a test-only oracle "
            "dependency (pixi.toml's [feature.pyforge-warden.dependencies]); "
            "2.2 explicitly SKIPS (never hard-fails) when a renderer isn't "
            "provisioned. Run this suite via "
            "`pixi run -e pyforge-warden pyforge-warden-test`."
        )
    return api


def _names_from_matchspecs(specs: list[str]) -> set[str]:
    """The leading NAME token of each rendered matchspec string (a
    deliberately dumb, independent tokenizer — never reuses this package's
    own ``extract/_identity.py`` parsing so the oracle stays a genuinely
    separate ground truth)."""
    names: set[str] = set()
    for spec in specs:
        tokens = spec.split()
        if tokens:
            names.add(tokens[0])
    return names


def test_recipe_v1_extraction_is_a_superset_of_the_rattler_build_render():
    rattler_build = _rattler_build_module()
    manifest = ScannedManifest(path="recipe.yaml", kind=RECIPE_YAML_KIND)
    components = RecipeV1Extractor(DefaultRouter()).extract(RECIPE_FIXTURE, manifest)
    extracted_names = {c.name for c in components}
    assert extracted_names, "the fixture must contribute at least one component"

    text = RECIPE_FIXTURE.read_text(encoding="utf-8")
    rendered = rattler_build.Stage0Recipe.from_yaml(text).render(
        rattler_build.VariantConfig.from_yaml("{}")
    )
    assert rendered, "the fixture must render to at least one variant"
    requirements = rendered[0].recipe.requirements.to_dict()
    rendered_names = _names_from_matchspecs(
        [*requirements.get("host", []), *requirements.get("run", [])]
    )
    assert rendered_names, "the fixture must render at least one requirement"

    assert extracted_names >= rendered_names
    # run_constraints must never leak into either side's comparison set.
    assert "scipy" not in extracted_names
    assert "scipy" not in rendered_names
    assert "scipy" in _names_from_matchspecs(requirements.get("run_constraints", []))


def test_meta_v0_extraction_is_a_superset_of_the_conda_build_render():
    api = _conda_build_module()
    manifest = ScannedManifest(path="meta.yaml", kind=META_YAML_KIND)
    components = MetaV0Extractor(DefaultRouter()).extract(META_FIXTURE, manifest)
    extracted_names = {c.name for c in components}
    assert extracted_names, "the fixture must contribute at least one component"

    metas = api.render(
        str(META_FIXTURE.parent), finalize=False, bypass_env_check=True
    )
    assert metas, "the fixture must render to at least one metadata object"
    meta = metas[0][0]
    rendered_run = meta.get_value("requirements/run") or []
    rendered_host = meta.get_value("requirements/host") or []
    rendered_names = _names_from_matchspecs([*rendered_run, *rendered_host])
    assert rendered_names, "the fixture must render at least one requirement"

    assert extracted_names >= rendered_names
    # run_constrained must never leak into either side's comparison set.
    assert "scipy" not in extracted_names
    assert "scipy" not in rendered_names
    rendered_constrained = _names_from_matchspecs(
        meta.get_value("requirements/run_constrained") or []
    )
    assert "scipy" in rendered_constrained


def test_recipe_v1_complex_extraction_is_a_superset_of_the_rattler_build_render():
    """Story 2.3's ratcheted oracle row: ``recipe_complex/recipe.yaml``
    exercises ``compiler()``/``stdlib()`` (build-tool exclude),
    ``if``/``then``/``else`` (selector-union, both branches), a second
    output's ``pin_subpackage()`` (intra-recipe exclude), and a
    name-resolved+expression-version degrade — all in ONE multi-output
    recipe, live-verified render included."""
    rattler_build = _rattler_build_module()
    manifest = ScannedManifest(path="recipe.yaml", kind=RECIPE_YAML_KIND)
    components = RecipeV1Extractor(DefaultRouter()).extract(
        RECIPE_COMPLEX_FIXTURE, manifest
    )
    extracted_names = {c.name for c in components}
    assert extracted_names, "the fixture must contribute at least one component"

    text = RECIPE_COMPLEX_FIXTURE.read_text(encoding="utf-8")
    # A populated variant config is REQUIRED here (unlike the common-case
    # test's empty `{}`): compiler()/stdlib() raise rather than render
    # without c_compiler/c_compiler_version/c_stdlib/c_stdlib_version, and
    # the if/then/else selector needs target_platform to pick a branch.
    variant_config = rattler_build.VariantConfig.from_yaml(
        "c_compiler: [gcc]\n"
        "c_compiler_version: ['12']\n"
        "c_stdlib: [sysroot]\n"
        "c_stdlib_version: ['2.17']\n"
        "target_platform: [linux-64]\n"
    )
    rendered = rattler_build.Stage0Recipe.from_yaml(text).render(variant_config)
    assert rendered, "the fixture must render to at least one variant"

    rendered_names: set[str] = set()
    for variant in rendered:
        requirements = variant.recipe.requirements.to_dict()
        for section in ("build", "host", "run"):
            entries = requirements.get(section) or []
            # pin_subpackage(...) renders to a non-string dict entry under
            # rattler_build -- filtered here before tokenizing (it would
            # otherwise crash `.split()`).
            string_entries = [e for e in entries if isinstance(e, str)]
            rendered_names |= _names_from_matchspecs(string_entries)
    assert rendered_names, "the fixture must render at least one requirement"
    rendered_names -= _BUILD_TOOL_RENDERED_NAMES

    assert extracted_names >= rendered_names
    # compiler()/stdlib()/pin_subpackage() must never leak into extraction's
    # OWN side either -- excluded entirely, never a Component.
    assert extracted_names.isdisjoint(_BUILD_TOOL_RENDERED_NAMES)
    assert _PIN_SUBPACKAGE_RENDERED_NAME not in extracted_names
    # Confirms the fixture actually exercises the build-tool construct (a
    # gap here would make the exclusion assertion above vacuous).
    all_build_entries = {
        entry
        for variant in rendered
        for entry in (variant.recipe.requirements.to_dict().get("build") or [])
        if isinstance(entry, str)
    }
    assert _BUILD_TOOL_RENDERED_NAMES <= _names_from_matchspecs(all_build_entries)


def test_meta_v0_complex_extraction_is_a_superset_of_the_conda_build_render():
    """Story 2.3's ratcheted oracle row: ``meta_complex/meta.yaml``
    exercises ``compiler()``/``stdlib()`` (build-tool exclude), two
    ``# [cond]`` sibling entries (selector-union), and a second output's
    ``pin_subpackage()`` (intra-recipe exclude)."""
    api = _conda_build_module()
    manifest = ScannedManifest(path="meta.yaml", kind=META_YAML_KIND)
    components = MetaV0Extractor(DefaultRouter()).extract(
        META_COMPLEX_FIXTURE, manifest
    )
    extracted_names = {c.name for c in components}
    assert extracted_names, "the fixture must contribute at least one component"

    metas = api.render(
        str(META_COMPLEX_FIXTURE.parent), finalize=False, bypass_env_check=True
    )
    assert metas, "the fixture must render to at least one metadata object"

    rendered_names: set[str] = set()
    build_names: set[str] = set()
    for meta, *_ in metas:
        rendered_run = meta.get_value("requirements/run") or []
        rendered_host = meta.get_value("requirements/host") or []
        rendered_build = meta.get_value("requirements/build") or []
        rendered_names |= _names_from_matchspecs(
            [*rendered_run, *rendered_host, *rendered_build]
        )
        build_names |= _names_from_matchspecs(rendered_build)
    assert rendered_names, "the fixture must render at least one requirement"
    rendered_names -= _BUILD_TOOL_RENDERED_NAMES
    # pin_subpackage(...) renders to a PLAIN STRING under conda_build
    # (unlike rattler_build's dict) -- an explicit name exclusion, since the
    # non-string filter used for rattler_build can't catch a string form.
    rendered_names.discard(_PIN_SUBPACKAGE_RENDERED_NAME)

    assert extracted_names >= rendered_names
    assert extracted_names.isdisjoint(_BUILD_TOOL_RENDERED_NAMES)
    assert _PIN_SUBPACKAGE_RENDERED_NAME not in extracted_names
    # Confirms the fixture actually exercises the build-tool construct.
    assert _BUILD_TOOL_RENDERED_NAMES <= build_names


def test_oracle_skips_cleanly_when_rattler_build_is_unavailable(monkeypatch):
    """Proves the skip-if-unavailable path is alive: never a hard block on
    renderer provisioning."""
    import builtins

    real_import = builtins.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "rattler_build":
            raise ImportError("simulated: renderer not provisioned")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocking_import)
    with pytest.raises(pytest.skip.Exception):
        _rattler_build_module()


def test_oracle_skips_cleanly_when_conda_build_is_unavailable(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "conda_build":
            raise ImportError("simulated: renderer not provisioned")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocking_import)
    with pytest.raises(pytest.skip.Exception):
        _conda_build_module()
