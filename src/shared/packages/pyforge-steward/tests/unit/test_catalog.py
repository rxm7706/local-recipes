"""Story 60.1 — the catalog config names backends and sources
(spec-self-hosted-bmad-marketplace CAP-1 / spec-pyforge-steward CAP-117).

Git is the edit store; backends and sources are declared in ``catalog.yaml``
and bound to plugins; a new backend or source is a plugin, not a rewrite.
"""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path

import pytest

from pyforge.steward.bootstrap import repo_root
from pyforge.steward.catalog import (
    CATALOG_RELATIVE,
    CLAUDE_MANIFEST_RELATIVE,
    CODEX_MANIFEST_RELATIVE,
    KIND_FRAME,
    KIND_MODULE,
    STATES,
    TIER_BMAD_CERTIFIED,
    TIER_UNVERIFIED,
    TRUST_TIERS,
    BackendDecl,
    BackendRegistry,
    CatalogConfigError,
    CatalogDuty,
    CatalogEngine,
    CatalogSourcePlugin,
    CondaChannelBackend,
    EstateListingsSource,
    GitBundleBackend,
    Listing,
    ObjectStorageBackend,
    ShipBackendPlugin,
    SourceContext,
    SourceRegistry,
    _github_owner_repo,
    default_catalog_dir,
    load_config,
)
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, EXIT_USAGE, build_parser, main, resolve_duty
from pyforge.steward.frames import EXPECTED_COUNT, preflight_frames
from pyforge.steward.suite import INSTALL_CLASS_MODULE, SUITE_PACKAGES

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_HEADER = """\
catalog:
  name: test-catalog
  display_name: Test catalog
  owner: tester
  description: a test catalog
  edit_store:
    kind: git
    repo: tester/repo
    path: catalog
    dedicated_repo: null
"""

_WIELDED_MODULE_COUNT = sum(1 for p in SUITE_PACKAGES if p.install_class == INSTALL_CLASS_MODULE)


def _write_catalog(tmp_path: Path, body: str, *, header: str = _HEADER) -> Path:
    """Write ``catalog/catalog.yaml`` under ``tmp_path`` and return the catalog dir."""
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    (catalog_dir / "catalog.yaml").write_text(header + textwrap.dedent(body), encoding="utf-8")
    return catalog_dir


def _engine(tmp_path: Path, body: str, *, root: Path | None = None) -> CatalogEngine:
    catalog_dir = _write_catalog(tmp_path, body)
    config = load_config(catalog_dir / "catalog.yaml")
    return CatalogEngine(root if root is not None else tmp_path, config, catalog_dir=catalog_dir)


class _CustomSource(CatalogSourcePlugin):
    """A source registered from outside the engine — the I/O-matrix row."""

    def __init__(self, rows: list[Listing] | None = None, plugin_name: str = "x") -> None:
        self._rows = rows if rows is not None else []
        self._name = plugin_name

    @property
    def name(self) -> str:
        return self._name

    def listings(self, ctx: SourceContext) -> list[Listing]:
        assert isinstance(ctx, SourceContext)
        return list(self._rows)


class _RaisingSource(CatalogSourcePlugin):
    def __init__(self, exc: Exception, plugin_name: str = "boom") -> None:
        self._exc = exc
        self._name = plugin_name

    @property
    def name(self) -> str:
        return self._name

    def listings(self, ctx: SourceContext) -> list[Listing]:
        raise self._exc


class _CustomBackend(ShipBackendPlugin):
    @property
    def name(self) -> str:
        return "y"

    def snapshot_target(self, decl: BackendDecl) -> str:
        return f"custom://{decl.name}"


def _row(name: str, source: str, **overrides) -> Listing:
    base = dict(
        name=name,
        kind=KIND_MODULE,
        source=source,
        trust_tier=TIER_UNVERIFIED,
        description=f"{name} desc",
        repository=f"https://github.com/acme/{name}",
    )
    base.update(overrides)
    return Listing(**base)


def _ns(**kwargs) -> argparse.Namespace:
    base = {"catalog_verb": "check", "json": False, "catalog": None, "check": False}
    base.update(kwargs)
    return argparse.Namespace(**base)


def _claude(engine: CatalogEngine) -> dict:
    return json.loads(engine.manifests()[CLAUDE_MANIFEST_RELATIVE.as_posix()])


# ---------------------------------------------------------------------------
# config load — the named failures
# ---------------------------------------------------------------------------


def test_load_config_missing_file_is_a_named_failure(tmp_path: Path) -> None:
    with pytest.raises(CatalogConfigError, match="catalog config not found"):
        load_config(tmp_path / "nope.yaml")


def test_load_config_malformed_yaml_is_a_named_failure(tmp_path: Path) -> None:
    path = tmp_path / "catalog.yaml"
    path.write_text("catalog: [unclosed\n", encoding="utf-8")
    with pytest.raises(CatalogConfigError, match="malformed YAML"):
        load_config(path)


def test_load_config_non_mapping_is_a_named_failure(tmp_path: Path) -> None:
    path = tmp_path / "catalog.yaml"
    path.write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(CatalogConfigError, match="top-level document must be a mapping"):
        load_config(path)


def test_load_config_unknown_state_is_a_named_failure(tmp_path: Path) -> None:
    catalog_dir = _write_catalog(
        tmp_path,
        """
        sources:
          s:
            plugin: p
            state: maybe
        """,
    )
    with pytest.raises(CatalogConfigError, match="'sources.s.state' = 'maybe' is not one of"):
        load_config(catalog_dir / "catalog.yaml")


def test_load_config_missing_plugin_on_an_on_row_is_a_named_failure(tmp_path: Path) -> None:
    catalog_dir = _write_catalog(
        tmp_path,
        """
        backends:
          b:
            state: "on"
        """,
    )
    with pytest.raises(CatalogConfigError, match="'backends.b' is 'on' but names no 'plugin'"):
        load_config(catalog_dir / "catalog.yaml")


def test_load_config_null_plugin_is_an_empty_slot_only_while_off(tmp_path: Path) -> None:
    catalog_dir = _write_catalog(
        tmp_path,
        """
        sources:
          slot: {plugin: null, state: "off"}
          later: {state: available}
        """,
    )
    config = load_config(catalog_dir / "catalog.yaml")
    assert [(s.name, s.plugin, s.state) for s in config.sources] == [
        ("slot", None, "off"),
        ("later", None, "available"),
    ]
    engine = CatalogEngine(tmp_path, config, catalog_dir=catalog_dir)
    assert engine.render(write=True).ok
    report = engine.check()
    assert report.ok
    assert report.slots == ("slot", "later")
    assert [(s["plugin"], s["bound"]) for s in report.sources] == [(None, False), (None, False)]
    catalog_dir = _write_catalog(tmp_path, 'sources:\n  slot: {plugin: "", state: "off"}\n')
    with pytest.raises(CatalogConfigError, match="'sources.slot.plugin' must be null"):
        load_config(catalog_dir / "catalog.yaml")


def test_load_config_rejects_a_boolean_or_empty_declaration_key(tmp_path: Path) -> None:
    catalog_dir = _write_catalog(tmp_path, 'backends:\n  on: {plugin: p, state: "off"}\n')
    with pytest.raises(CatalogConfigError, match="'backends' key True must be a non-empty string"):
        load_config(catalog_dir / "catalog.yaml")
    catalog_dir = _write_catalog(tmp_path, 'sources:\n  "": {plugin: p, state: "off"}\n')
    with pytest.raises(CatalogConfigError, match="'sources' key '' must be a non-empty string"):
        load_config(catalog_dir / "catalog.yaml")


def test_load_config_rejects_a_misspelled_top_level_section(tmp_path: Path) -> None:
    catalog_dir = _write_catalog(tmp_path, 'backend:\n  b: {plugin: p, state: "on"}\nsourcez: {}\n')
    with pytest.raises(CatalogConfigError, match=r"unknown top-level key\(s\) \['backend', 'sourcez'\]"):
        load_config(catalog_dir / "catalog.yaml")


def test_load_config_requires_git_as_the_edit_store(tmp_path: Path) -> None:
    header = _HEADER.replace("kind: git", "kind: svn")
    catalog_dir = _write_catalog(tmp_path, "", header=header)
    with pytest.raises(CatalogConfigError, match="'catalog.edit_store.kind' = 'svn'; git is the edit store"):
        load_config(catalog_dir / "catalog.yaml")


@pytest.mark.parametrize("value", ["https://github.com/x/y", "git@github.com:x/y", "x", "x/y/z", "x/y#readme"])
def test_load_config_dedicated_repo_must_be_owner_repo(tmp_path: Path, value: str) -> None:
    header = _HEADER.replace("dedicated_repo: null", f"dedicated_repo: {value!r}")
    catalog_dir = _write_catalog(tmp_path, "", header=header)
    with pytest.raises(CatalogConfigError, match="dedicated_repo' must be null or an owner/repo string"):
        load_config(catalog_dir / "catalog.yaml")


@pytest.mark.parametrize(
    ("body", "needle"),
    [
        ("catalog: 3\n", "'catalog' section missing"),
        ("catalog:\n  name: x\n  owner: ''\n", "'catalog.owner' is required"),
        ("catalog:\n  name: x\n  owner: o\n", "'catalog.edit_store' section missing"),
        (
            "catalog:\n  name: x\n  owner: o\n  edit_store: {kind: git, repo: r, path: p, dedicated_repo: 7}\n",
            "dedicated_repo' must be null or an owner/repo string",
        ),
        (_HEADER + "sources: [a]\n", "'sources' section must be a mapping"),
        (_HEADER + "sources:\n  s: plugin\n", "'sources.s' must be a mapping"),
    ],
)
def test_load_config_other_named_failures(tmp_path: Path, body: str, needle: str) -> None:
    path = tmp_path / "catalog.yaml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(CatalogConfigError, match=needle):
        load_config(path)


def test_load_config_normalizes_bare_yaml_booleans_to_state_words(tmp_path: Path) -> None:
    """Bare ``on``/``off`` are YAML 1.1 booleans — accepted as the words they were."""
    catalog_dir = _write_catalog(
        tmp_path,
        """
        backends:
          a: {plugin: pa, state: on, channel: c}
          b: {plugin: pb, state: off}
          c: {plugin: pc, state: available}
        """,
    )
    config = load_config(catalog_dir / "catalog.yaml")
    assert [b.state for b in config.backends] == list(STATES)
    assert config.backends[0].options == {"channel": "c"}
    assert config.edit_store.dedicated_repo is None
    assert config.display_name == "Test catalog"


def test_load_config_empty_display_name_falls_back_to_name(tmp_path: Path) -> None:
    for header in (
        _HEADER.replace("display_name: Test catalog", 'display_name: ""'),
        _HEADER.replace("display_name: Test catalog", "display_name: 7"),
        _HEADER.replace("  display_name: Test catalog\n", ""),
    ):
        catalog_dir = _write_catalog(tmp_path, "", header=header)
        config = load_config(catalog_dir / "catalog.yaml")
        assert config.display_name == "test-catalog"
        engine = CatalogEngine(tmp_path, config, catalog_dir=catalog_dir)
        codex = json.loads(engine.manifests()[CODEX_MANIFEST_RELATIVE.as_posix()])
        assert codex["interface"] == {"displayName": "test-catalog"}


# ---------------------------------------------------------------------------
# registries — a plugin slot, not a rewrite
# ---------------------------------------------------------------------------


def test_duplicate_registration_raises() -> None:
    sources = SourceRegistry()
    sources.register(_CustomSource())
    with pytest.raises(ValueError, match="source 'x' is already registered"):
        sources.register(_CustomSource())
    backends = BackendRegistry()
    backends.register(_CustomBackend())
    with pytest.raises(ValueError, match="backend 'y' is already registered"):
        backends.register(_CustomBackend())
    assert sources.names() == ["x"] and backends.names() == ["y"]
    assert "x" in sources and "nope" not in sources
    with pytest.raises(KeyError):
        sources.get("nope")


def test_engine_self_registers_the_defaults(tmp_path: Path) -> None:
    engine = _engine(tmp_path, "")
    assert engine.sources.names() == ["estate-frames", "estate-listings", "wielded-suite"]
    assert engine.backends.names() == ["conda-channel", "git-bundle", "object-storage"]


def test_io_matrix_new_source_is_a_plugin_slot_not_a_rewrite(tmp_path: Path) -> None:
    """Declare a new source + backend `on`; without the plugins → `slot-unbound`
    only; register them on the engine (no engine edit) → ok."""
    engine = _engine(
        tmp_path,
        """
        backends:
          mine: {plugin: y, state: "on"}
        sources:
          extra: {plugin: x, state: "on"}
        """,
    )
    assert engine.render(write=True).ok  # manifests in sync so binding is the only question
    report = engine.check()
    assert [f.code for f in report.findings] == ["slot-unbound", "slot-unbound"]
    assert {f.subject for f in report.findings} == {"backends.mine", "sources.extra"}
    assert report.ok is False

    engine.sources.register(_CustomSource([_row("thing", "extra")]))
    engine.backends.register(_CustomBackend())
    assert engine.render(write=True).ok
    report = engine.check()
    assert report.ok, report.findings
    assert report.listing_count == 1
    assert [b["snapshot_target"] for b in report.backends] == ["custom://mine"]
    assert [s["listings"] for s in report.sources] == [1]
    assert report.slots == ()


def test_declared_off_without_a_plugin_is_a_slot_and_ok(tmp_path: Path) -> None:
    engine = _engine(
        tmp_path,
        """
        backends:
          later: {plugin: nope, state: available}
        sources:
          skills: {plugin: skillsctl, state: "off"}
        """,
    )
    assert engine.render(write=True).ok
    report = engine.check()
    assert report.ok
    assert report.slots == ("later", "skills")
    assert [b["bound"] for b in report.backends] == [False]
    assert [s["bound"] for s in report.sources] == [False]


def test_a_backend_that_raises_never_aborts_check(tmp_path: Path) -> None:
    class Broken(ShipBackendPlugin):
        @property
        def name(self) -> str:
            return "broken"

        def snapshot_target(self, decl: BackendDecl) -> str:
            raise RuntimeError("boom")

    engine = _engine(tmp_path, 'backends:\n  b: {plugin: broken, state: "on"}\n')
    engine.backends.register(Broken())
    assert engine.render(write=True).ok
    report = engine.check()
    assert [f.code for f in report.findings] == ["config-backend"]
    assert "boom" in report.findings[0].message
    assert report.backends[0]["snapshot_target"] is None


def test_a_source_that_raises_anything_is_a_config_source_finding_and_others_still_run(
    tmp_path: Path,
) -> None:
    engine = _engine(
        tmp_path,
        """
        sources:
          bad: {plugin: boom, state: "on"}
          good: {plugin: x, state: "on"}
        """,
    )
    engine.sources.register(_RaisingSource(UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad byte")))
    engine.sources.register(_CustomSource([_row("fine", "good")]))
    report = engine.check()
    assert [(f.code, f.subject) for f in report.findings] == [("config-source", "sources.bad")]
    assert report.findings[0].message.startswith("UnicodeDecodeError: ")
    assert [s["listings"] for s in report.sources] == [0, 1]
    assert [r.name for r in engine.listings()] == ["fine"]


def test_a_raising_source_refuses_render_and_render_check(tmp_path: Path) -> None:
    engine = _engine(
        tmp_path,
        """
        sources:
          bad: {plugin: boom, state: "on"}
          good: {plugin: x, state: "on"}
        """,
    )
    engine.sources.register(_RaisingSource(RuntimeError("plugin author bug")))
    engine.sources.register(_CustomSource([_row("fine", "good")]))
    rendered = engine.render(write=True)
    assert rendered.ok is False
    assert [(f.code, f.subject) for f in rendered.findings] == [("config-source", "sources.bad")]
    assert "RuntimeError: plugin author bug" in rendered.findings[0].message
    assert rendered.manifests == {} and rendered.written == ()
    assert not (engine.catalog_dir / CLAUDE_MANIFEST_RELATIVE).exists()
    assert not (engine.catalog_dir / CODEX_MANIFEST_RELATIVE).exists()
    assert [f.code for f in engine.drift()] == ["config-source"]  # never "in sync"


# ---------------------------------------------------------------------------
# every listing names a source
# ---------------------------------------------------------------------------


def _estate_engine(tmp_path: Path, estate_yaml: str, extra_sources: str = "") -> CatalogEngine:
    engine = _engine(
        tmp_path,
        """
        sources:
          estate-listings: {plugin: estate-listings, state: "on", path: registry/estate.yaml}
        """
        + extra_sources,
    )
    registry = engine.catalog_dir / "registry"
    registry.mkdir()
    (registry / "estate.yaml").write_text(textwrap.dedent(estate_yaml), encoding="utf-8")
    return engine


def test_estate_row_naming_another_source_is_a_mismatch_and_is_withheld(tmp_path: Path) -> None:
    engine = _estate_engine(
        tmp_path,
        """
        source: estate-listings
        modules:
          - name: good
            repository: https://github.com/acme/good
            trust_tier: community-reviewed
          - name: stray
            source: other
            repository: https://github.com/acme/stray
        """,
    )
    rendered = engine.render(write=True)
    assert rendered.ok is False and rendered.written == ()
    report = engine.check()
    assert [(f.code, f.subject) for f in report.findings] == [("listing-source-mismatch", "stray")]
    rows = engine.listings()
    assert [(r.name, r.source, r.trust_tier) for r in rows] == [
        ("good", "estate-listings", "community-reviewed"),
    ]
    assert [p["name"] for p in _claude(engine)["plugins"]] == ["good"]


def test_estate_row_with_empty_source_is_listing_no_source_and_is_withheld(tmp_path: Path) -> None:
    engine = _estate_engine(
        tmp_path,
        """
        modules:
          - name: blank
            source: ""
            repository: https://github.com/acme/blank
        """,
    )
    assert [f.code for f in engine.check().findings] == ["listing-no-source"]
    assert engine.listings() == []
    assert _claude(engine)["plugins"] == []


def test_estate_file_level_source_must_be_estate_listings(tmp_path: Path) -> None:
    engine = _estate_engine(tmp_path, "source: other\nmodules: []\n")
    report = engine.check()
    assert [f.code for f in report.findings] == ["config-source"]
    assert "must say 'estate-listings'" in report.findings[0].message


def test_estate_file_level_source_absent_means_estate_listings(tmp_path: Path) -> None:
    engine = _estate_engine(tmp_path, "modules:\n  - {name: a, repository: https://github.com/acme/a}\n")
    (row,) = engine.listings()
    assert row.source == "estate-listings"
    assert engine.render(write=True).ok


@pytest.mark.parametrize(
    ("estate_yaml", "needle"),
    [
        ("modules: 3\n", "'modules' must be a list"),
        ("modules:\n  - 3\n", "modules[0] must be a mapping"),
        ("modules:\n  - {repository: r}\n", "modules[0].name is required"),
        ("- a\n", "top-level document must be a mapping"),
        (
            "modules:\n  - {name: a, repository: https://github.com/acme/a, trust_tier: bmad-certifed}\n",
            "modules[0].trust_tier = 'bmad-certifed' is not one of",
        ),
    ],
)
def test_malformed_estate_registry_is_a_config_finding_and_refuses_render(
    tmp_path: Path, estate_yaml: str, needle: str
) -> None:
    engine = _estate_engine(tmp_path, estate_yaml)
    rendered = engine.render(write=True)
    assert rendered.ok is False and rendered.written == ()
    assert not (engine.catalog_dir / CLAUDE_MANIFEST_RELATIVE).exists()
    findings = engine.check().findings
    assert [f.code for f in findings] == ["config-source"]
    assert needle in findings[0].message
    assert [f.code for f in engine.drift()] == ["config-source"]


def test_estate_trust_tiers_are_exactly_the_upstream_enum(tmp_path: Path) -> None:
    assert TRUST_TIERS == ("unverified", "community-reviewed", "bmad-certified")
    rows = "\n".join(
        f"  - {{name: m{i}, repository: https://github.com/acme/m{i}, trust_tier: {tier}}}"
        for i, tier in enumerate(TRUST_TIERS)
    )
    engine = _estate_engine(tmp_path, f"modules:\n{rows}\n")
    assert [r.trust_tier for r in engine.listings()] == list(TRUST_TIERS)
    assert [p["tags"][1] for p in _claude(engine)["plugins"]] == [f"trust:{t}" for t in TRUST_TIERS]


def test_missing_estate_registry_is_a_config_finding(tmp_path: Path) -> None:
    engine = _engine(
        tmp_path,
        'sources:\n  estate-listings: {plugin: estate-listings, state: "on"}\n',
    )
    ctx = SourceContext(tmp_path, engine.catalog_dir, engine.config, engine.config.sources[0])
    with pytest.raises(CatalogConfigError, match="estate listings not found"):
        EstateListingsSource().listings(ctx)


def test_estate_path_null_means_the_default_registry(tmp_path: Path) -> None:
    engine = _engine(
        tmp_path,
        'sources:\n  estate-listings: {plugin: estate-listings, state: "on", path: null}\n',
    )
    registry = engine.catalog_dir / "registry"
    registry.mkdir()
    (registry / "estate.yaml").write_text(
        "modules:\n  - {name: a, repository: https://github.com/acme/a}\n", encoding="utf-8"
    )
    assert [r.name for r in engine.listings()] == ["a"]


def test_estate_version_follows_the_recipe_version_rule(tmp_path: Path) -> None:
    engine = _estate_engine(
        tmp_path,
        """
        modules:
          - {name: s, repository: https://github.com/acme/s, version: "1.10"}
          - {name: i, repository: https://github.com/acme/i, version: 3}
          - {name: f, repository: https://github.com/acme/f, version: 1.10}
          - {name: b, repository: https://github.com/acme/b, version: true}
          - {name: l, repository: https://github.com/acme/l, version: [1]}
          - {name: n, repository: https://github.com/acme/n}
        """,
    )
    assert [r.version for r in engine.listings()] == ["1.10", "3", None, None, None, None]
    assert [p.get("version") for p in _claude(engine)["plugins"]] == ["1.10", "3", None, None, None, None]


def test_estate_row_carries_every_listing_field(tmp_path: Path) -> None:
    engine = _estate_engine(
        tmp_path,
        """
        modules:
          - name: full
            description: a full row
            repository: https://github.com/acme/full.git
            homepage: https://acme.example/full
            version: 1.2.3
            code: fl
            install_hint: pixi add full
            codex_source: ./plugins/full
            trust_tier: bmad-certified
            display_name: Full       # upstream field, preserved but not read
        """,
    )
    (row,) = engine.listings()
    assert row.to_dict() == {
        "name": "full",
        "kind": KIND_MODULE,
        "source": "estate-listings",
        "trust_tier": TIER_BMAD_CERTIFIED,
        "description": "a full row",
        "repository": "https://github.com/acme/full.git",
        "version": "1.2.3",
        "code": "fl",
        "install_hint": "pixi add full",
        "link": "https://acme.example/full",
        "codex_source": "./plugins/full",
    }
    manifests = engine.manifests()
    claude = json.loads(manifests[CLAUDE_MANIFEST_RELATIVE.as_posix()])
    assert claude["plugins"][0]["source"] == {"source": "github", "repo": "acme/full"}
    codex = json.loads(manifests[CODEX_MANIFEST_RELATIVE.as_posix()])
    assert codex["plugins"] == [
        {
            "name": "full",
            "source": {"source": "local", "path": "./plugins/full"},
            "policy": {"installation": "AVAILABLE"},
            "category": KIND_MODULE,
        }
    ]


def test_two_listings_with_the_same_kind_and_name_are_a_duplicate(tmp_path: Path) -> None:
    engine = _estate_engine(
        tmp_path,
        """
        modules:
          - {name: bmad-builder, repository: https://github.com/acme/bmad-builder}
          - {name: twice, repository: https://github.com/acme/twice}
          - {name: twice, repository: https://github.com/acme/twice}
        """,
        extra_sources='  wielded-suite: {plugin: wielded-suite, state: "on"}\n',
    )
    findings = engine.check().findings
    assert [(f.code, f.subject) for f in findings] == [
        ("listing-duplicate", "twice"),
        ("listing-duplicate", "bmad-builder"),
    ]
    assert "'estate-listings' and by 'estate-listings'" in findings[0].message
    assert "'estate-listings' and by 'wielded-suite'" in findings[1].message
    assert engine.render(write=True).ok is False
    # a frame and a module may share a name: the key is (kind, name)
    engine = _engine(tmp_path, 'sources:\n  extra: {plugin: x, state: "on"}\n')
    engine.sources.register(_CustomSource([_row("same", "extra"), _row("same", "extra", kind=KIND_FRAME)]))
    assert engine.render(write=True).ok
    assert engine.check().ok
    assert [(r.kind, r.name) for r in engine.listings()] == [(KIND_MODULE, "same"), (KIND_FRAME, "same")]


@pytest.mark.parametrize(
    ("repository", "expected"),
    [
        ("https://github.com/acme/x", "acme/x"),
        ("https://github.com/acme/x.git/", "acme/x"),
        ("github.com/acme/x", "acme/x"),
        ("acme/x", "acme/x"),
        ("acme/x.y-z_1", "acme/x.y-z_1"),
        ("git@github.com:acme/x", None),
        ("git@github.com:acme/x.git", None),
        ("acme/x#readme", None),
        ("acme/x?tab=readme", None),
        ("acme/my repo", None),
        ("https://github.com/acme", None),
        ("https://github.com/acme/x/tree/main", None),
        ("https://gitlab.com/acme/x", None),
        ("", None),
        (None, None),
    ],
)
def test_github_owner_repo_accepts_exactly_two_safe_segments(repository: str | None, expected: str | None) -> None:
    assert _github_owner_repo(repository) == expected


# ---------------------------------------------------------------------------
# the wielded-suite and estate-frames sources reuse, never re-parse
# ---------------------------------------------------------------------------


def test_wielded_rows_derive_from_suite_packages_module_class_only(tmp_path: Path) -> None:
    engine = _engine(tmp_path, 'sources:\n  wielded-suite: {plugin: wielded-suite, state: "on"}\n')
    rows = engine.listings()
    expected = [p.name for p in SUITE_PACKAGES if p.install_class == INSTALL_CLASS_MODULE]
    assert [r.name for r in rows] == expected
    assert expected == [
        "bmad-method-test-architecture-enterprise",
        "bmad-builder",
        "bmad-creative-intelligence-suite",
        "bmad-utility-skills",
    ]
    assert {r.trust_tier for r in rows} == {TIER_BMAD_CERTIFIED}
    assert {r.kind for r in rows} == {KIND_MODULE}
    assert {r.source for r in rows} == {"wielded-suite"}
    # tmp repo root has no recipes/ — description/version fail open, never raise
    assert {r.description for r in rows} == {""}
    assert {r.version for r in rows} == {None}
    by_name = {r.name: r for r in rows}
    assert by_name["bmad-builder"].install_hint == "steward provision --module bmb"
    assert by_name["bmad-utility-skills"].install_hint == "steward provision --module utility-skills"


def _write_frame(path: Path, identifier: str, *, inherits: str | None, missing: str | None = None) -> None:
    fields = {
        "type": "frame",
        "identifier": identifier,
        "name": identifier.split("/")[-1].title(),
        "description": f"{identifier} frame",
        "visibility": "private",
        "version": "0.1.0",
    }
    if missing:
        fields.pop(missing)
    lines = ["---"] + [f"{k}: {v}" for k, v in fields.items()] + ["maintainer:", "  - steward"]
    if inherits:
        lines += ["inherits:", f"  - {inherits}"]
    lines += ["---", "", f"# {identifier}", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def test_frame_rows_come_from_preflight_and_skip_frames_that_fail_it(tmp_path: Path) -> None:
    frames = tmp_path / "docs" / "foundry" / "frames"
    _write_frame(frames / "pyforge.frame.md", "pyforge/company", inherits=None)
    _write_frame(frames / "stations" / "atlas.frame.md", "pyforge/atlas", inherits="pyforge/company")
    _write_frame(
        frames / "stations" / "doctor.frame.md",
        "pyforge/doctor",
        inherits="pyforge/company",
        missing="description",
    )
    engine = _engine(
        tmp_path,
        'sources:\n  estate-frames: {plugin: estate-frames, state: "on", path: docs/foundry/frames}\n',
    )
    rows = engine.listings()
    assert [r.name for r in rows] == ["pyforge/company", "pyforge/atlas"]
    assert {r.kind for r in rows} == {KIND_FRAME}
    assert {r.trust_tier for r in rows} == {TIER_UNVERIFIED}
    assert rows[1].link == "docs/foundry/frames/stations/atlas.frame.md"
    assert rows[1].install_hint == "load docs/foundry/frames/stations/atlas.frame.md"
    assert rows[1].repository == "https://github.com/tester/repo"
    assert rows[1].version == "0.1.0"
    # frames never render into the Claude manifest (module rows only)
    assert _claude(engine)["plugins"] == []
    # `path: null` is absent → the default frames root (the same tmp tree here)
    engine = _engine(tmp_path, 'sources:\n  estate-frames: {plugin: estate-frames, state: "on", path: null}\n')
    assert [r.name for r in engine.listings()] == ["pyforge/company", "pyforge/atlas"]


# ---------------------------------------------------------------------------
# render — both manifests, their required keys, and drift
# ---------------------------------------------------------------------------


def test_render_writes_both_manifests_with_required_keys(tmp_path: Path) -> None:
    engine = _engine(tmp_path, 'sources:\n  extra: {plugin: x, state: "on"}\n')
    engine.sources.register(
        _CustomSource(
            [
                _row("mod", "extra", version="1.0"),
                _row("frame-ish", "extra", kind=KIND_FRAME),
                _row("gitlab", "extra", repository="https://gitlab.com/a/b"),
                _row("ssh", "extra", repository="git@github.com:acme/ssh.git"),
            ]
        )
    )
    rendered = engine.render(write=True)
    assert rendered.ok
    assert set(rendered.manifests) == {CLAUDE_MANIFEST_RELATIVE.as_posix(), CODEX_MANIFEST_RELATIVE.as_posix()}
    assert rendered.written == (
        str(engine.catalog_dir / CLAUDE_MANIFEST_RELATIVE),
        str(engine.catalog_dir / CODEX_MANIFEST_RELATIVE),
    )
    claude = json.loads((engine.catalog_dir / CLAUDE_MANIFEST_RELATIVE).read_text(encoding="utf-8"))
    assert claude["name"] == "test-catalog"
    assert claude["owner"] == {"name": "tester"}
    assert [p["name"] for p in claude["plugins"]] == ["mod", "gitlab", "ssh"]  # module rows only
    mod, gitlab, ssh = claude["plugins"]
    assert mod["source"] == {"source": "github", "repo": "acme/mod"}
    assert mod["version"] == "1.0"
    assert mod["tags"] == ["source:extra", f"trust:{TIER_UNVERIFIED}"]
    # a non-GitHub git URL is Claude Code's documented url form, never dropped
    assert gitlab["source"] == {"source": "url", "url": "https://gitlab.com/a/b"}
    # the SSH form is not owner/repo, so it is a url source, never `git@…` as `repo`
    assert ssh["source"] == {"source": "url", "url": "git@github.com:acme/ssh.git"}
    codex = json.loads((engine.catalog_dir / CODEX_MANIFEST_RELATIVE).read_text(encoding="utf-8"))
    assert codex == {
        "name": "test-catalog",
        "interface": {"displayName": "Test catalog"},
        "plugins": [],
    }
    assert engine.drift() == []


def test_a_module_listing_without_a_repository_is_a_finding_not_a_silent_omission(tmp_path: Path) -> None:
    engine = _engine(tmp_path, 'sources:\n  extra: {plugin: x, state: "on"}\n')
    engine.sources.register(
        _CustomSource([_row("no-repo", "extra", repository=None), _row("blank", "extra", repository="  ")])
    )
    report = engine.check()
    assert [(f.code, f.subject) for f in report.findings] == [
        ("listing-no-repository", "no-repo"),
        ("listing-no-repository", "blank"),
    ]
    rendered = engine.render(write=True)
    assert rendered.ok is False and rendered.written == ()
    assert not (engine.catalog_dir / CLAUDE_MANIFEST_RELATIVE).exists()


def test_a_listing_change_without_rerender_is_manifest_drift(tmp_path: Path) -> None:
    engine = _engine(tmp_path, 'sources:\n  extra: {plugin: x, state: "on"}\n')
    source = _CustomSource([_row("one", "extra")])
    engine.sources.register(source)
    assert engine.render(write=True).ok
    assert engine.check().ok
    source._rows.append(_row("two", "extra"))
    report = engine.check()
    assert [f.code for f in report.findings] == ["manifest-drift"]
    assert report.findings[0].subject == CLAUDE_MANIFEST_RELATIVE.as_posix()
    assert "stale" in report.findings[0].message
    assert [f.code for f in engine.drift()] == ["manifest-drift"]


# ---------------------------------------------------------------------------
# the duty + CLI front door
# ---------------------------------------------------------------------------


def test_catalog_is_the_twentieth_duty_and_resolves() -> None:
    assert isinstance(resolve_duty("catalog"), CatalogDuty)
    ns = build_parser().parse_args(["catalog", "render", "--check", "--json"])
    assert (ns.catalog_verb, ns.check, ns.json) == ("render", True, True)
    ns = build_parser().parse_args(["catalog", "--catalog", "/tmp/x"])
    assert (ns.catalog_verb, ns.catalog, ns.json) == (None, "/tmp/x", False)


@pytest.mark.parametrize(
    ("argv", "verb", "catalog", "as_json"),
    [
        (["catalog", "--json"], None, None, True),
        (["catalog", "--catalog", "D"], None, "D", False),
        (["catalog", "--catalog", "D", "--json"], None, "D", True),
        (["catalog", "check", "--catalog", "D"], "check", "D", False),
        (["catalog", "check", "--json"], "check", None, True),
        (["catalog", "--json", "check"], "check", None, True),
        (["catalog", "--catalog", "D", "check"], "check", "D", False),
        (["catalog", "--catalog", "D", "list", "--json"], "list", "D", True),
        (["catalog", "--json", "render", "--check", "--catalog", "D"], "render", "D", True),
        (["catalog", "pointers", "--catalog", "D", "--json"], "pointers", "D", True),
    ],
)
def test_catalog_and_json_flags_parse_before_or_after_the_verb(argv, verb, catalog, as_json) -> None:
    ns = build_parser().parse_args(argv)
    assert (ns.catalog_verb, ns.catalog, ns.json) == (verb, catalog, as_json)


def test_cli_json_with_the_verb_omitted_runs_check(tmp_path: Path, capsys) -> None:
    catalog_dir = _write_catalog(tmp_path, "")
    assert (
        CatalogEngine(tmp_path, load_config(catalog_dir / "catalog.yaml"), catalog_dir=catalog_dir)
        .render(write=True)
        .ok
    )
    rc = main(["catalog", "--catalog", str(catalog_dir), "--json"])
    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True and payload["slots"] == []
    rc = main(["catalog", "check", "--catalog", str(catalog_dir)])
    assert rc == EXIT_OK
    assert "catalog check: ok" in capsys.readouterr().out
    assert rc != EXIT_USAGE


def test_cli_slot_unbound_is_the_only_finding_and_exits_1(tmp_path: Path, capsys) -> None:
    """AC: a new source `on` with `plugin: x` and no plugin `x` registered."""
    catalog_dir = _write_catalog(tmp_path, 'sources:\n  extra: {plugin: x, state: "on"}\n')
    config = load_config(catalog_dir / "catalog.yaml")
    assert CatalogEngine(tmp_path, config, catalog_dir=catalog_dir).render(write=True).ok
    rc = main(["catalog", "--catalog", str(catalog_dir), "check", "--json"])
    assert rc == EXIT_FAILED
    payload = json.loads(capsys.readouterr().err)
    assert payload["ok"] is False
    assert [f["code"] for f in payload["findings"]] == ["slot-unbound"]
    assert payload["findings"][0]["subject"] == "sources.extra"
    assert payload["sources"] == [{"name": "extra", "plugin": "x", "state": "on", "bound": False, "listings": 0}]
    rc = main(["catalog", "--catalog", str(catalog_dir), "check"])
    assert rc == EXIT_FAILED
    assert "[slot-unbound] sources.extra" in capsys.readouterr().err


def test_cli_render_check_reports_drift_and_render_repairs_it(tmp_path: Path, capsys) -> None:
    catalog_dir = _write_catalog(tmp_path, "")
    rc = main(["catalog", "--catalog", str(catalog_dir), "render", "--check"])
    assert rc == EXIT_FAILED
    assert "manifest-drift" in capsys.readouterr().err
    rc = main(["catalog", "--catalog", str(catalog_dir), "render", "--json"])
    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True and payload["findings"] == []
    assert all(Path(p).is_file() for p in payload["written"]) and len(payload["written"]) == 2
    rc = main(["catalog", "--catalog", str(catalog_dir), "render", "--check", "--json"])
    assert rc == EXIT_OK
    assert json.loads(capsys.readouterr().out) == {"ok": True, "findings": []}
    rc = main(["catalog", "--catalog", str(catalog_dir), "render", "--check"])
    assert rc == EXIT_OK
    assert "manifests in sync" in capsys.readouterr().out
    # off/available-only declarations: the listing is empty, and says so
    rc = main(["catalog", "--catalog", str(catalog_dir), "list"])
    assert rc == EXIT_OK
    assert "no listings" in capsys.readouterr().out


def test_cli_render_refuses_on_a_broken_source_and_writes_nothing(tmp_path: Path, capsys) -> None:
    catalog_dir = _write_catalog(
        tmp_path,
        'sources:\n  estate-listings: {plugin: estate-listings, state: "on"}\n',
    )
    (catalog_dir / "registry").mkdir()
    (catalog_dir / "registry" / "estate.yaml").write_text("modules: 3\n", encoding="utf-8")
    rc = main(["catalog", "--catalog", str(catalog_dir), "render", "--json"])
    assert rc == EXIT_FAILED
    payload = json.loads(capsys.readouterr().err)
    assert payload["ok"] is False and payload["written"] == []
    assert [f["code"] for f in payload["findings"]] == ["config-source"]
    assert not (catalog_dir / CLAUDE_MANIFEST_RELATIVE).exists()
    rc = main(["catalog", "--catalog", str(catalog_dir), "render"])
    assert rc == EXIT_FAILED
    assert "refused, nothing written" in capsys.readouterr().err
    rc = main(["catalog", "--catalog", str(catalog_dir), "render", "--check"])
    assert rc == EXIT_FAILED
    assert "[config-source]" in capsys.readouterr().err


def test_cli_config_load_failure_is_a_duty_failure_not_a_crash(tmp_path: Path, capsys) -> None:
    rc = main(["catalog", "--catalog", str(tmp_path), "check"])
    assert rc == EXIT_FAILED
    assert "catalog config not found" in capsys.readouterr().err
    rc = main(["catalog", "--catalog", str(tmp_path), "list", "--json"])
    assert rc == EXIT_FAILED
    payload = json.loads(capsys.readouterr().err)
    assert [f["code"] for f in payload["findings"]] == ["config-load"]


def test_duty_never_raises_past_its_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> Path:
        raise RuntimeError("no checkout")

    monkeypatch.setattr("pyforge.steward.catalog.repo_root", boom)
    result = CatalogDuty().run(_ns())
    assert result.ok is False
    assert result.summary == "catalog check failed: RuntimeError: no checkout"
    result = CatalogDuty().run(_ns(catalog_verb="list", json=True))
    assert result.ok is False
    assert json.loads(result.summary) == {
        "ok": False,
        "findings": [{"code": "internal", "subject": "list", "message": "RuntimeError: no checkout"}],
    }


def test_duty_unknown_verb_names_the_verbs(tmp_path: Path) -> None:
    catalog_dir = _write_catalog(tmp_path, "")
    result = CatalogDuty().run(_ns(catalog_verb="bogus", catalog=str(catalog_dir)))
    assert result.ok is False
    assert "available verbs are check, list, render, pointers" in result.summary


def test_pointers_name_every_consumer_form_and_edit_nothing(tmp_path: Path, capsys) -> None:
    settings = repo_root() / ".claude" / "settings.json"
    before = settings.read_bytes() if settings.is_file() else None
    catalog_dir = _write_catalog(tmp_path, "")
    rc = main(["catalog", "--catalog", str(catalog_dir), "pointers"])
    assert rc == EXIT_OK
    out = capsys.readouterr().out
    assert f"bmad-method install --custom-source {catalog_dir.resolve()}" in out
    assert '"extraKnownMarketplaces"' in out and '"source": "directory"' in out
    assert f"/plugin marketplace add {catalog_dir.resolve()}" in out
    assert "codex plugin marketplace add <owner/repo>" in out
    assert "wait on edit_store.dedicated_repo" in out
    assert ".claude/settings.json is not edited" in out
    # verified live 2026-09-19: bmad-method 6.12.0 resolves the dir but "Found 0 modules"
    assert "Found 0 modules" in out and "until 60.3" in out
    after = settings.read_bytes() if settings.is_file() else None
    assert before == after

    rc = main(["catalog", "--catalog", str(catalog_dir), "pointers", "--json"])
    assert rc == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["extra_known_marketplaces"] == {
        "extraKnownMarketplaces": {
            "test-catalog": {"source": {"source": "directory", "path": str(catalog_dir.resolve())}}
        }
    }
    assert payload["dedicated_repo"] is None


def test_pointers_quote_a_catalog_path_with_a_space(tmp_path: Path) -> None:
    spaced = tmp_path / "my catalog"
    spaced.mkdir()
    (spaced / "catalog.yaml").write_text(_HEADER, encoding="utf-8")
    engine = CatalogEngine(tmp_path, load_config(spaced / "catalog.yaml"), catalog_dir=spaced)
    pointers = engine.pointers()
    quoted = f"'{spaced.resolve()}'"
    assert pointers["custom_source"] == f"bmad-method install --custom-source {quoted}"
    assert pointers["claude_plugin_add"] == f"/plugin marketplace add {quoted}"
    assert pointers["catalog_dir"] == str(spaced.resolve())  # the raw path stays raw


def test_pointers_use_the_github_forms_once_a_dedicated_repo_is_confirmed(tmp_path: Path) -> None:
    header = _HEADER.replace("dedicated_repo: null", "dedicated_repo: tester/catalog")
    catalog_dir = _write_catalog(tmp_path, "", header=header)
    engine = CatalogEngine(tmp_path, load_config(catalog_dir / "catalog.yaml"), catalog_dir=catalog_dir)
    pointers = engine.pointers()
    assert pointers["codex_plugin_add"] == "codex plugin marketplace add tester/catalog"
    assert pointers["extra_known_marketplaces"]["extraKnownMarketplaces"]["test-catalog"] == {
        "source": {"source": "directory", "path": "catalog"}
    }
    assert "github forms available" in pointers["github_note"]


def test_backends_read_declared_options_and_treat_null_as_absent() -> None:
    def decl(name: str, **options) -> BackendDecl:
        return BackendDecl(name=name, plugin=name, state="on", options=options)

    conda = CondaChannelBackend()
    assert conda.snapshot_target(decl("conda-channel")) == "conda://SelfExplainML/pyforge-estate-catalog"
    assert conda.snapshot_target(decl("conda-channel", channel="c", package="p")) == "conda://c/p"
    assert (
        conda.snapshot_target(decl("conda-channel", channel=None, package=None))
        == "conda://SelfExplainML/pyforge-estate-catalog"
    )
    s3 = ObjectStorageBackend()
    assert s3.snapshot_target(decl("object-storage", bucket=None, key=None)) == "s3://<bucket>/catalog/snapshot.tar.gz"
    assert s3.snapshot_target(decl("object-storage", bucket="b", key="k")) == "s3://b/k"
    bundle = GitBundleBackend()
    assert bundle.snapshot_target(decl("git-bundle", file=None)) == "catalog.bundle"
    assert bundle.snapshot_target(decl("git-bundle", file="x.bundle")) == "x.bundle"


# ---------------------------------------------------------------------------
# the committed tree — the AC as a live test
# ---------------------------------------------------------------------------


def test_real_tree_check_is_ok_and_manifests_are_in_sync(capsys) -> None:
    root = repo_root()
    assert default_catalog_dir(root) == root / CATALOG_RELATIVE
    rc = main(["catalog", "check", "--json"])
    assert rc == EXIT_OK, capsys.readouterr().err
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["slots"] == ["object-storage", "git-bundle", "public-bmad-catalog", "claude-skill-registry"]
    assert {(b["name"], b["state"]) for b in report["backends"]} == {
        ("conda-channel", "on"),
        ("object-storage", "off"),
        ("git-bundle", "available"),
    }
    assert {(s["name"], s["state"]) for s in report["sources"]} == {
        ("estate-listings", "on"),
        ("wielded-suite", "on"),
        ("public-bmad-catalog", "off"),
        ("estate-frames", "on"),
        ("claude-skill-registry", "off"),
    }
    by_name = {s["name"]: s for s in report["sources"]}
    assert (by_name["claude-skill-registry"]["plugin"], by_name["claude-skill-registry"]["bound"]) == (None, False)
    assert by_name["public-bmad-catalog"]["plugin"] == "public-bmad-catalog"
    assert report["catalog"]["edit_store"] == {
        "kind": "git",
        "repo": "rxm7706/local-recipes",
        "path": CATALOG_RELATIVE.as_posix(),
        "dedicated_repo": None,
    }
    assert main(["catalog", "render", "--check"]) == EXIT_OK
    assert main(["catalog"]) == EXIT_OK  # bare invocation defaults to check


def test_real_tree_list_names_a_declared_source_on_every_listing(capsys) -> None:
    root = repo_root()
    assert main(["catalog", "list", "--json"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    declared = {"estate-listings", "wielded-suite", "estate-frames"}
    rows = payload["listings"]
    assert payload["count"] == len(rows) == _WIELDED_MODULE_COUNT + EXPECTED_COUNT
    assert all(r["source"] and r["source"] in declared for r in rows)
    wielded = [r for r in rows if r["source"] == "wielded-suite"]
    assert [r["name"] for r in wielded] == [p.name for p in SUITE_PACKAGES if p.install_class == INSTALL_CLASS_MODULE]
    assert {r["trust_tier"] for r in wielded} == {TIER_BMAD_CERTIFIED}
    assert all(r["version"] and r["description"] for r in wielded)  # recipes present
    frames = [r for r in rows if r["source"] == "estate-frames"]
    expected = sorted(str(doc.fields["identifier"]).strip() for doc in preflight_frames(root).frames)
    assert sorted(r["name"] for r in frames) == expected
    assert len(frames) == EXPECTED_COUNT  # a tenth frame fails in frames.py first
    assert {r["kind"] for r in frames} == {KIND_FRAME}


def test_real_tree_claude_manifest_has_the_discovery_shape() -> None:
    manifest = json.loads((default_catalog_dir() / CLAUDE_MANIFEST_RELATIVE).read_text(encoding="utf-8"))
    assert manifest["name"] == "pyforge-estate-catalog"
    assert manifest["owner"]["name"] == "rxm7706"
    assert isinstance(manifest["plugins"], list) and len(manifest["plugins"]) == _WIELDED_MODULE_COUNT
    for plugin in manifest["plugins"]:
        assert plugin["name"]
        assert plugin["source"]["source"] == "github"
        assert _github_owner_repo(plugin["source"]["repo"]) == plugin["source"]["repo"]
        assert any(tag.startswith("source:") for tag in plugin["tags"])
        assert any(tag.startswith("trust:") for tag in plugin["tags"])
    codex = json.loads((default_catalog_dir() / CODEX_MANIFEST_RELATIVE).read_text(encoding="utf-8"))
    assert codex["plugins"] == []  # no wielded module ships a .codex-plugin dir


def test_real_tree_pointers_use_the_repo_relative_directory_form(capsys) -> None:
    assert main(["catalog", "pointers", "--json"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["extra_known_marketplaces"] == {
        "extraKnownMarketplaces": {
            "pyforge-estate-catalog": {
                "source": {"source": "directory", "path": "src/shared/packages/pyforge-steward/catalog"}
            }
        }
    }
    assert payload["dedicated_repo"] is None
    assert payload["catalog_dir"] == str((repo_root() / CATALOG_RELATIVE).resolve())


def test_real_tree_estate_registry_is_empty_and_names_its_source() -> None:
    import yaml

    registry = yaml.safe_load((default_catalog_dir() / "registry" / "estate.yaml").read_text(encoding="utf-8"))
    assert registry == {"source": "estate-listings", "modules": []}
