"""Unit tests — the Gap-B identity + merge rules (Story 1.1).

Every merge rule of the I/O matrix: provenance-list union, bare-version
folding, never-guess-attribute, distinct versions kept, purl derivation,
identity comparison ignoring purl qualifiers, PEP 503 name canonicalization,
and the commutative conservative conflict policy (merge never upgrades
confidence). These rules are load-bearing for SBOM/report counts.
"""

from __future__ import annotations

import pytest

from python_deptry_osv_scanner.inventory import (
    Provenance,
    PypiIdentity,
    ResolvedInventory,
    canonical_name,
    derive_purl,
    identity,
    merge_components,
    strip_purl_qualifiers,
)
from python_deptry_osv_scanner.models import (
    CveMatchLevel,
    Ecosystem,
    IdentitySource,
    ScannedManifest,
    WithholdReason,
)


def test_same_identity_merges_to_one_with_provenance_union(component_factory):
    host = component_factory(provenance=(("meta.yaml", "host"),))
    run = component_factory(provenance=(("meta.yaml", "run"),))
    merged = merge_components([host, run])
    assert len(merged) == 1
    assert merged[0].provenance == (
        Provenance(manifest="meta.yaml", section="host"),
        Provenance(manifest="meta.yaml", section="run"),
    )


def test_duplicate_provenance_entries_deduplicate(component_factory):
    first = component_factory(provenance=(("meta.yaml", "run"),))
    second = component_factory(provenance=(("meta.yaml", "run"),))
    merged = merge_components([first, second])
    assert len(merged) == 1
    assert merged[0].provenance == (Provenance(manifest="meta.yaml", section="run"),)


def test_bare_folds_into_sole_concrete_version(component_factory):
    bare = component_factory(
        version=None,
        provenance=(("environment.yml", "dependencies"),),
        indeterminate_reason=WithholdReason.NO_VERSION,
    )
    concrete = component_factory(provenance=(("pixi.lock", "pypi"),))
    merged = merge_components([bare, concrete])
    assert len(merged) == 1
    assert merged[0].version == "2.31.0"
    assert merged[0].provenance == (
        Provenance(manifest="environment.yml", section="dependencies"),
        Provenance(manifest="pixi.lock", section="pypi"),
    )


def test_bare_folds_regardless_of_feed_order(component_factory):
    bare = component_factory(version=None, provenance=(("environment.yml", "deps"),))
    concrete = component_factory(provenance=(("pixi.lock", "pypi"),))
    for feed in ([bare, concrete], [concrete, bare]):
        merged = merge_components(feed)
        assert len(merged) == 1
        assert merged[0].version == "2.31.0"
        assert len(merged[0].provenance) == 2


def test_fold_keeps_the_concrete_sides_fields(component_factory):
    """A fold unions provenance ONLY — the bare record's version-driven
    deficiencies (withhold reason, weak match level, unmatchability) do not
    survive; the concrete side's fields win."""
    bare = component_factory(
        version=None,
        provenance=(("environment.yml", "dependencies"),),
        indeterminate_reason=WithholdReason.NO_VERSION,
        cve_match_level=CveMatchLevel.NAME_ONLY,
        vuln_matchable=False,
    )
    concrete = component_factory(provenance=(("pixi.lock", "pypi"),))
    for feed in ([bare, concrete], [concrete, bare]):
        merged = merge_components(feed)
        assert len(merged) == 1
        assert merged[0].indeterminate_reason is None
        assert merged[0].cve_match_level is CveMatchLevel.EXACT
        assert merged[0].vuln_matchable is True


def test_bare_alone_stays_distinct_indeterminate(component_factory):
    bare = component_factory(
        version=None, indeterminate_reason=WithholdReason.NO_VERSION
    )
    merged = merge_components([bare])
    assert len(merged) == 1
    assert merged[0].version is None
    assert merged[0].indeterminate_reason is WithholdReason.NO_VERSION


def test_bare_with_two_concrete_versions_never_guess_attributes(component_factory):
    bare = component_factory(
        version=None, indeterminate_reason=WithholdReason.NO_VERSION
    )
    one = component_factory(version="1.0")
    two = component_factory(version="2.0")
    merged = merge_components([bare, one, two])
    assert len(merged) == 3
    bare_out = [c for c in merged if c.version is None]
    assert len(bare_out) == 1
    assert bare_out[0].indeterminate_reason is WithholdReason.NO_VERSION
    assert sorted(c.version for c in merged if c.version is not None) == ["1.0", "2.0"]


def test_two_versions_stay_distinct(component_factory):
    merged = merge_components(
        [component_factory(version="1.0"), component_factory(version="2.0")]
    )
    assert len(merged) == 2
    assert {c.version for c in merged} == {"1.0", "2.0"}


def test_bare_never_folds_across_ecosystems(component_factory):
    bare_conda = component_factory(
        version=None,
        ecosystem=Ecosystem.CONDA,
        indeterminate_reason=WithholdReason.NO_VERSION,
    )
    concrete_pypi = component_factory(ecosystem=Ecosystem.PYPI)
    merged = merge_components([bare_conda, concrete_pypi])
    assert len(merged) == 2


def test_canonical_name_pep503_for_pypi_unchanged_for_conda():
    assert canonical_name(Ecosystem.PYPI, "Django") == "django"
    assert canonical_name(Ecosystem.PYPI, "typing_extensions") == "typing-extensions"
    assert canonical_name(Ecosystem.PYPI, "zope.interface") == "zope-interface"
    assert canonical_name(Ecosystem.PYPI, "a.-_b") == "a-b"
    assert canonical_name(Ecosystem.CONDA, "ruamel.yaml") == "ruamel.yaml"
    assert canonical_name(Ecosystem.CONDA, "PyYAML") == "PyYAML"


def test_derive_purl_forms():
    assert derive_purl(Ecosystem.PYPI, "requests", "2.31.0") == "pkg:pypi/requests@2.31.0"
    assert derive_purl(Ecosystem.CONDA, "numpy", "1.26.4") == "pkg:conda/numpy@1.26.4"
    assert derive_purl(Ecosystem.PYPI, "requests", None) == "pkg:pypi/requests"


def test_derive_purl_uses_canonical_purl_names():
    assert derive_purl(Ecosystem.PYPI, "Django", "5.0") == "pkg:pypi/django@5.0"
    assert (
        derive_purl(Ecosystem.PYPI, "typing_extensions", "4.12")
        == "pkg:pypi/typing-extensions@4.12"
    )
    # conda: lowercase, _ -> -, dots preserved.
    assert derive_purl(Ecosystem.CONDA, "ruamel.yaml", "0.18") == "pkg:conda/ruamel.yaml@0.18"
    assert derive_purl(Ecosystem.CONDA, "typing_extensions", "4.12") == "pkg:conda/typing-extensions@4.12"
    assert derive_purl(Ecosystem.CONDA, "PyYAML", "6.0") == "pkg:conda/pyyaml@6.0"


def test_derive_purl_empty_version_omits_at():
    assert derive_purl(Ecosystem.PYPI, "requests", "") == "pkg:pypi/requests"
    assert derive_purl(Ecosystem.CONDA, "numpy", "") == "pkg:conda/numpy"


def test_strip_purl_qualifiers():
    assert (
        strip_purl_qualifiers("pkg:conda/numpy@1.26.4?build=py312h2b&channel=conda-forge")
        == "pkg:conda/numpy@1.26.4"
    )
    assert strip_purl_qualifiers("pkg:pypi/foo@1.0#sub/path") == "pkg:pypi/foo@1.0"
    assert strip_purl_qualifiers("pkg:pypi/foo@1.0") == "pkg:pypi/foo@1.0"


def test_identity_is_field_derived_tuple(component_factory):
    component = component_factory()
    assert identity(component) == (Ecosystem.PYPI, "requests", "2.31.0")


def test_identity_is_pep503_canonical_for_pypi(component_factory):
    spelled = component_factory(name="Typing_Extensions", version="4.12")
    canonical = component_factory(name="typing-extensions", version="4.12")
    assert identity(spelled) == identity(canonical)
    assert identity(spelled)[1] == "typing-extensions"


def test_identity_empty_string_version_normalizes_to_none(component_factory):
    empty = component_factory(version="")
    bare = component_factory(version=None)
    assert identity(empty) == identity(bare)
    assert identity(empty)[2] is None


def test_identity_comparison_ignores_purl_qualifiers(component_factory):
    plain = component_factory(purl="pkg:pypi/requests@2.31.0")
    qualified = component_factory(
        purl="pkg:pypi/requests@2.31.0?os=linux#src",
        provenance=(("pixi.toml", "run"),),
    )
    assert identity(plain) == identity(qualified)
    assert strip_purl_qualifiers(qualified.purl) == plain.purl
    merged = merge_components([plain, qualified])
    assert len(merged) == 1
    assert len(merged[0].provenance) == 2


def test_merge_is_feed_order_invariant_under_conflicts(component_factory):
    """merge(a, b) == merge(b, a) even when non-provenance fields conflict."""
    a = component_factory(cve_match_level=CveMatchLevel.EXACT)
    b = component_factory(
        cve_match_level=CveMatchLevel.NAME_ONLY,
        purl="pkg:pypi/requests@2.31.0?os=linux#src",
        provenance=(("pixi.toml", "run"),),
    )
    forward = merge_components([a, b])
    backward = merge_components([b, a])
    assert forward == backward
    assert len(forward) == 1
    merged = forward[0]
    # Least-confident match level survives; the differing purl re-derives
    # (which also strips the qualifiers).
    assert merged.cve_match_level is CveMatchLevel.NAME_ONLY
    assert merged.purl == "pkg:pypi/requests@2.31.0"


def test_merge_ands_coverage_booleans(component_factory):
    covered = component_factory(hygiene_covered=True, vuln_matchable=True)
    uncovered = component_factory(
        hygiene_covered=False,
        vuln_matchable=False,
        provenance=(("pixi.toml", "run"),),
    )
    for feed in ([covered, uncovered], [uncovered, covered]):
        merged = merge_components(feed)
        assert len(merged) == 1
        assert merged[0].hygiene_covered is False
        assert merged[0].vuln_matchable is False


def test_merge_keeps_least_confident_match_level(component_factory):
    exact = component_factory(cve_match_level=CveMatchLevel.EXACT)
    none = component_factory(
        cve_match_level=CveMatchLevel.NONE, provenance=(("pixi.toml", "run"),)
    )
    for feed in ([exact, none], [none, exact]):
        merged = merge_components(feed)
        assert merged[0].cve_match_level is CveMatchLevel.NONE


def test_merge_withholds_ambiguous_pypi_identity(component_factory):
    """Two differing non-None pypi identities: ambiguity is withheld, never
    guessed — identity None, source none, confidence None."""
    torch = component_factory(
        ecosystem=Ecosystem.CONDA,
        name="pytorch",
        pypi_identity=PypiIdentity(name="torch", version="2.31.0"),
        identity_source=IdentitySource.MAP,
        mapping_confidence="verified",
    )
    pytorch = component_factory(
        ecosystem=Ecosystem.CONDA,
        name="pytorch",
        pypi_identity=PypiIdentity(name="pytorch", version="2.31.0"),
        identity_source=IdentitySource.LOCK,
        mapping_confidence="verified",
        provenance=(("pixi.lock", "conda"),),
    )
    for feed in ([torch, pytorch], [pytorch, torch]):
        merged = merge_components(feed)
        assert len(merged) == 1
        assert merged[0].pypi_identity is None
        assert merged[0].identity_source is IdentitySource.NONE
        assert merged[0].mapping_confidence is None


def test_merge_keeps_single_sided_pypi_identity(component_factory):
    unresolved = component_factory(
        ecosystem=Ecosystem.CONDA,
        name="pytorch",
        pypi_identity=None,
        identity_source=IdentitySource.NONE,
    )
    resolved = component_factory(
        ecosystem=Ecosystem.CONDA,
        name="pytorch",
        pypi_identity=PypiIdentity(name="torch", version="2.31.0"),
        identity_source=IdentitySource.MAP,
        mapping_confidence="verified",
        provenance=(("pixi.lock", "conda"),),
    )
    for feed in ([unresolved, resolved], [resolved, unresolved]):
        merged = merge_components(feed)
        assert len(merged) == 1
        assert merged[0].pypi_identity == PypiIdentity(name="torch", version="2.31.0")
        assert merged[0].identity_source is IdentitySource.MAP
        assert merged[0].mapping_confidence == "verified"


@pytest.mark.parametrize(
    ("spelling_a", "spelling_b"),
    [("Django", "django"), ("typing_extensions", "typing-extensions")],
    ids=["case", "underscore"],
)
def test_pep503_spellings_merge_to_canonical(component_factory, spelling_a, spelling_b):
    a = component_factory(name=spelling_a, version="5.0", pypi_identity=None)
    b = component_factory(
        name=spelling_b,
        version="5.0",
        pypi_identity=None,
        provenance=(("pixi.toml", "run"),),
    )
    for feed in ([a, b], [b, a]):
        merged = merge_components(feed)
        assert len(merged) == 1
        assert merged[0].name == canonical_name(Ecosystem.PYPI, spelling_a)
        assert len(merged[0].provenance) == 2


def test_empty_string_version_folds_like_a_bare_entry(component_factory):
    empty = component_factory(
        version="",
        provenance=(("environment.yml", "dependencies"),),
    )
    concrete = component_factory(provenance=(("pixi.lock", "pypi"),))
    for feed in ([empty, concrete], [concrete, empty]):
        merged = merge_components(feed)
        assert len(merged) == 1
        assert merged[0].version == "2.31.0"
        assert len(merged[0].provenance) == 2


def test_merge_output_ordering_is_deterministic(component_factory):
    components = [
        component_factory(name="zlib", ecosystem=Ecosystem.CONDA, version="1.3"),
        component_factory(name="requests", version="2.0"),
        component_factory(name="requests", version="1.0"),
    ]
    assert merge_components(components) == merge_components(reversed(components))


def test_resolved_inventory_count_is_post_merge(component_factory):
    merged = merge_components(
        [
            component_factory(provenance=(("meta.yaml", "host"),)),
            component_factory(provenance=(("meta.yaml", "run"),)),
            component_factory(
                name="numpy", version="1.26.4", ecosystem=Ecosystem.CONDA
            ),
        ]
    )
    inventory = ResolvedInventory(
        components=merged,
        resolved_scan_set=(ScannedManifest(path="meta.yaml", kind="meta-v0"),),
    )
    assert inventory.count == 2
    assert inventory.count == len(inventory.components)


def test_resolved_inventory_rejects_duplicate_identities(component_factory):
    """The inventory is post-merge by contract — same identity twice raises."""
    first = component_factory(provenance=(("meta.yaml", "host"),))
    second = component_factory(provenance=(("meta.yaml", "run"),))
    with pytest.raises(ValueError, match="post-merge"):
        ResolvedInventory(components=(first, second), resolved_scan_set=())
    # PEP-503-equivalent spellings collide too.
    with pytest.raises(ValueError, match="post-merge"):
        ResolvedInventory(
            components=(
                component_factory(name="Django", version="5.0"),
                component_factory(name="django", version="5.0"),
            ),
            resolved_scan_set=(),
        )
