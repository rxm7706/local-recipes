"""The differential-oracle — ``RecipeV1Extractor``/``MetaV0Extractor`` vs.
``rattler_build``/``conda_build``'s real renderers (Story 2.2, ratcheted by
Story 2.3's complex-construct fixtures, MATURED to corpus scale by Story
5.2).

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

Story 5.2 (fleet-scale maturation) ADDS two corpus-scale tests
(``test_corpus_recipe_v1_extraction_is_a_superset_of_the_rattler_build_render``/
``test_corpus_meta_v0_extraction_is_a_superset_of_the_conda_build_render``)
walking the FULL committed ``tests/fixtures/corpus/`` (recipes + adversarial)
rather than replacing the 4 hand-authored precision fixtures above — those
stay (they assert EXACT excluded-name sets no corpus-scale sweep could
replicate, e.g. "``gcc_linux-64``/``sysroot_linux-64`` are excluded on both
sides"; live-verified renders against curated fixtures remain the most
precise regression pin for those specific constructs). The corpus-scale
tests instead prove the SAME superset property holds broadly across ~2,000
real-world recipes, with two necessary generalizations spelled out in their
own docstrings: (1) name comparison is case-INSENSITIVE (conda package
names are canonically lowercase; a real corpus recipe surfaced a verbatim-
cased dependency, e.g. ``PyPDF2``, that the renderer normalizes but our
extractor — correctly — preserves as authored) and (2) a file is excluded
from the strict per-file comparison (not from the corpus-scale render
ATTEMPT, which still must not raise) when either its raw text uses
``compiler()``/``stdlib()``/``pin_subpackage()`` (excluded EXCLUDED, never a
Component, exactly like the existing complex fixtures — but corpus scale
can't hardcode every possible resolved compiler-package name) or our own
extraction already degraded ≥1 component (``RAW_MALFORMED``/``NAME_ONLY``
— by definition not something we can claim superset parity over). The
WHOLE MODULE is marked ``@pytest.mark.slow`` (not just the two new tests):
every test here needs a real renderer import, and the render-based oracle
concept itself — corpus-scale or not — is documented (Boundaries) as never
belonging in the fast default suite; it runs via the separate
``pyforge-warden-test-corpus-oracle`` pixi task instead.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pyforge.warden.discovery import META_YAML_KIND, RECIPE_YAML_KIND
from pyforge.warden.extract import UnparsableManifestError
from pyforge.warden.extract.meta_v0 import MetaV0Extractor
from pyforge.warden.extract.recipe_v1 import RecipeV1Extractor
from pyforge.warden.models import ExtractionMode, ScannedManifest
from pyforge.warden.routing import DefaultRouter

pytestmark = pytest.mark.slow

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "projects"
RECIPE_FIXTURE = FIXTURES / "recipe_common" / "recipe.yaml"
META_FIXTURE = FIXTURES / "meta_common" / "meta.yaml"
RECIPE_COMPLEX_FIXTURE = FIXTURES / "recipe_complex" / "recipe.yaml"
META_COMPLEX_FIXTURE = FIXTURES / "meta_complex" / "meta.yaml"

CORPUS_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "corpus"
# A file using any of these constructs is excluded from the STRICT
# per-file superset comparison at corpus scale (see module docstring) —
# never from the render/extract ATTEMPT itself, which must still not raise.
_EXCLUDED_CONSTRUCT_RE = re.compile(r"compiler\(|stdlib\(|pin_subpackage\(")
_DEGRADED_MODES = (ExtractionMode.RAW_MALFORMED, ExtractionMode.NAME_ONLY)
# A slightly less "dumb" tokenizer than the fixture-scale
# ``_names_from_matchspecs`` below (kept untouched for the 4 precision
# tests that already pass with it): real corpus recipes occasionally embed
# a PEP 508-style, no-space version pin directly in a v0 meta.yaml list
# (e.g. ``chardet>=3.0.4``) — live-verified corpus finding — which a plain
# ``.split()`` cannot separate from its operator. Matches up to the first
# whitespace or comparison-operator character; identical to ``.split()[0]``
# whenever a space DOES separate name from operator (every fixture-scale
# case above), so this is a strict generalization, not a behavior change
# for the cases the simpler tokenizer already handled correctly.
_NAME_TOKEN_RE = re.compile(r"^[^\s<>=!~]+")
# Sanity floors (NOT the exact measured counts, which will drift as the
# corpus is re-harvested) — guard against the corpus-scale comparison
# silently degenerating to "compared far fewer files than expected" (e.g.
# a partial render regression from an unrelated environment change) and
# passing vacuously. Measured this story: 228 recipe.yaml / 711 meta.yaml
# files were eligible for the strict comparison, 0 violations either side
# — these floors sit ~9-12% below that measurement (review finding: the
# original floors were 150/400, wide enough to mask a genuine ~1/3 drop in
# compared-file count as a pass; tightened, still with real slack for
# legitimate corpus-composition drift across re-harvests).
_MINIMUM_COMPARED_RECIPE_YAML = 200
_MINIMUM_COMPARED_META_YAML = 650

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


# --- Story 5.2: corpus-scale sweep (see module docstring for the two
# generalizations relative to the fixture-scale tests above) ----------------


def _corpus_names_from_matchspecs(specs: list[str]) -> set[str]:
    """Like ``_names_from_matchspecs`` above, but tolerant of a no-space
    matchspec (``chardet>=3.0.4``) and lowercased (conda names are
    canonically case-insensitive) — see the module docstring/
    ``_NAME_TOKEN_RE`` comment for why corpus scale needs this."""
    names: set[str] = set()
    for spec in specs:
        match = _NAME_TOKEN_RE.match(spec)
        if match:
            names.add(match.group(0).lower())
    return names


def test_corpus_recipe_v1_extraction_is_a_superset_of_the_rattler_build_render():
    rattler_build = _rattler_build_module()
    # A broad, best-effort variant config covering the keys real corpus
    # recipes most commonly need for their ``compiler()``/``stdlib()``/
    # ``python_min`` context to resolve at all (live-calibrated this story:
    # raised a ~35% sample render-success rate to ~97% on a 150-file
    # sample). A file that STILL fails to render under this config (missing
    # a project-specific context var no generic config could anticipate) is
    # simply not oracle-verifiable — it contributes to ``not_rendered``
    # below, never a test failure (this is a coverage sweep, not a claim
    # that 100% of an arbitrary, unrelated-repo's recipes must render
    # standalone).
    variant_config = rattler_build.VariantConfig.from_yaml(
        "python_min: ['3.11']\n"
        "target_platform: [linux-64]\n"
        "c_compiler: [gcc]\n"
        "c_compiler_version: ['13']\n"
        "cxx_compiler: [gxx]\n"
        "cxx_compiler_version: ['13']\n"
        "c_stdlib: [sysroot]\n"
        "c_stdlib_version: ['2.17']\n"
        "fortran_compiler: [gfortran]\n"
        "fortran_compiler_version: ['13']\n"
        "rust_compiler: [rust]\n"
    )
    router = DefaultRouter()
    extractor = RecipeV1Extractor(router)

    files = sorted(CORPUS_DIR.rglob("recipe.yaml"))
    assert files, "the committed corpus must contain recipe.yaml files"

    compared = 0
    violations: list[str] = []
    for path in files:
        manifest = ScannedManifest(path=path.name, kind=RECIPE_YAML_KIND)
        try:
            components = extractor.extract(path, manifest)
        except UnparsableManifestError:
            continue  # not oracle-verifiable; test_corpus_regression.py owns this count
        text = path.read_text(encoding="utf-8")
        try:
            rendered = rattler_build.Stage0Recipe.from_yaml(text).render(variant_config)
        except (SystemExit, Exception):  # noqa: BLE001 — a render failure here
            # just means this file isn't oracle-verifiable with a generic
            # variant config (see the config's own comment above) — never a
            # bug in OUR extractor, so it's excluded from the assertion set
            # rather than failing the sweep.
            continue
        if not rendered:
            continue
        if _EXCLUDED_CONSTRUCT_RE.search(text) or any(
            c.extraction_mode in _DEGRADED_MODES for c in components
        ):
            continue
        extracted_names = {c.name.lower() for c in components}
        rendered_names: set[str] = set()
        for variant in rendered:
            requirements = variant.recipe.requirements.to_dict()
            for section in ("build", "host", "run"):
                entries = requirements.get(section) or []
                string_entries = [e for e in entries if isinstance(e, str)]
                rendered_names |= _corpus_names_from_matchspecs(string_entries)
        compared += 1
        missing = rendered_names - extracted_names
        if missing:
            violations.append(f"{path}: extraction missing {sorted(missing)}")

    assert not violations, (
        f"{len(violations)} corpus recipe.yaml file(s) rendered names our "
        "extraction did not cover:\n" + "\n".join(violations[:20])
    )
    assert compared >= _MINIMUM_COMPARED_RECIPE_YAML, (
        f"only {compared} corpus recipe.yaml files were oracle-verifiable "
        f"(expected >= {_MINIMUM_COMPARED_RECIPE_YAML}) — the comparison "
        "may be degenerating vacuously"
    )


def test_corpus_meta_v0_extraction_is_a_superset_of_the_conda_build_render():
    api = _conda_build_module()
    router = DefaultRouter()
    extractor = MetaV0Extractor(router)

    files = sorted(CORPUS_DIR.rglob("meta.yaml"))
    assert files, "the committed corpus must contain meta.yaml files"

    compared = 0
    violations: list[str] = []
    for path in files:
        manifest = ScannedManifest(path=path.name, kind=META_YAML_KIND)
        try:
            components = extractor.extract(path, manifest)
        except UnparsableManifestError:
            continue  # not oracle-verifiable; test_corpus_regression.py owns this count
        text = path.read_text(encoding="utf-8")
        try:
            metas = api.render(str(path.parent), finalize=False, bypass_env_check=True)
        except (SystemExit, Exception):  # noqa: BLE001 — see the recipe.yaml
            # sweep above: conda_build itself calls sys.exit() on some
            # malformed real-world meta.yaml files (live-verified —
            # "Error: bad character '*' in package name dependency '*'"),
            # so SystemExit is caught alongside Exception here exactly like
            # cli.py's own engine seam does.
            continue
        if not metas:
            continue
        if _EXCLUDED_CONSTRUCT_RE.search(text) or any(
            c.extraction_mode in _DEGRADED_MODES for c in components
        ):
            continue
        extracted_names = {c.name.lower() for c in components}
        rendered_names: set[str] = set()
        for meta, *_rest in metas:
            rendered_run = meta.get_value("requirements/run") or []
            rendered_host = meta.get_value("requirements/host") or []
            rendered_build = meta.get_value("requirements/build") or []
            rendered_names |= _corpus_names_from_matchspecs(
                [*rendered_run, *rendered_host, *rendered_build]
            )
        compared += 1
        missing = rendered_names - extracted_names
        if missing:
            violations.append(f"{path}: extraction missing {sorted(missing)}")

    assert not violations, (
        f"{len(violations)} corpus meta.yaml file(s) rendered names our "
        "extraction did not cover:\n" + "\n".join(violations[:20])
    )
    assert compared >= _MINIMUM_COMPARED_META_YAML, (
        f"only {compared} corpus meta.yaml files were oracle-verifiable "
        f"(expected >= {_MINIMUM_COMPARED_META_YAML}) — the comparison "
        "may be degenerating vacuously"
    )
