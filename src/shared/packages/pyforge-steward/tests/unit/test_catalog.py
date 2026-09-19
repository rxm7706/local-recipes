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
    BackendDecl,
    BackendRegistry,
    CatalogConfigError,
    CatalogDuty,
    CatalogEngine,
    CatalogSourcePlugin,
    CondaChannelBackend,
    EstateListingsSource,
    Listing,
    ShipBackendPlugin,
    SourceContext,
    SourceRegistry,
    default_catalog_dir,
    load_config,
)
from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, build_parser, main, resolve_duty
from pyforge.steward.frames import preflight_frames
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


def test_load_config_missing_plugin_is_a_named_failure(tmp_path: Path) -> None:
    catalog_dir = _write_catalog(
        tmp_path,
        """
        backends:
          b:
            state: "on"
        """,
    )
    with pytest.raises(CatalogConfigError, match="'backends.b' is missing 'plugin'"):
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
    engine.render(write=True)  # manifests in sync so binding is the only question
    report = engine.check()
    assert [f.code for f in report.findings] == ["slot-unbound", "slot-unbound"]
    assert {f.subject for f in report.findings} == {"backends.mine", "sources.extra"}
    assert report.ok is False

    engine.sources.register(_CustomSource([_row("thing", "extra")]))
    engine.backends.register(_CustomBackend())
    engine.render(write=True)
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
    engine.render(write=True)
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
    engine.render(write=True)
    report = engine.check()
    assert [f.code for f in report.findings] == ["config-backend"]
    assert "boom" in report.findings[0].message
    assert report.backends[0]["snapshot_target"] is None


# ---------------------------------------------------------------------------
# every listing names a source
# ---------------------------------------------------------------------------


def _estate_engine(tmp_path: Path, estate_yaml: str) -> CatalogEngine:
    engine = _engine(
        tmp_path,
        """
        sources:
          estate-listings: {plugin: estate-listings, state: "on", path: registry/estate.yaml}
        """,
    )
    registry = engine.catalog_dir / "registry"
    registry.mkdir()
    (registry / "estate.yaml").write_text(textwrap.dedent(estate_yaml), encoding="utf-8")
    return engine


def test_estate_row_naming_another_source_is_a_mismatch(tmp_path: Path) -> None:
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
    engine.render(write=True)
    report = engine.check()
    assert [(f.code, f.subject) for f in report.findings] == [("listing-source-mismatch", "stray")]
    rows = engine.listings()
    assert [(r.name, r.source, r.trust_tier) for r in rows] == [
        ("good", "estate-listings", "community-reviewed"),
        ("stray", "other", TIER_UNVERIFIED),
    ]


def test_estate_row_with_empty_source_is_listing_no_source(tmp_path: Path) -> None:
    engine = _estate_engine(
        tmp_path,
        """
        modules:
          - name: blank
            source: ""
            repository: https://github.com/acme/blank
        """,
    )
    engine.render(write=True)
    assert [f.code for f in engine.check().findings] == ["listing-no-source"]


def test_estate_file_level_source_must_be_estate_listings(tmp_path: Path) -> None:
    engine = _estate_engine(tmp_path, "source: other\nmodules: []\n")
    engine.render(write=True)
    report = engine.check()
    assert [f.code for f in report.findings] == ["config-source"]
    assert "must say 'estate-listings'" in report.findings[0].message


@pytest.mark.parametrize(
    ("estate_yaml", "needle"),
    [
        ("modules: 3\n", "'modules' must be a list"),
        ("modules:\n  - 3\n", "modules[0] must be a mapping"),
        ("modules:\n  - {repository: r}\n", "modules[0].name is required"),
        ("- a\n", "top-level document must be a mapping"),
    ],
)
def test_malformed_estate_registry_is_a_config_finding(
    tmp_path: Path, estate_yaml: str, needle: str
) -> None:
    engine = _estate_engine(tmp_path, estate_yaml)
    engine.render(write=True)
    findings = engine.check().findings
    assert [f.code for f in findings] == ["config-source"]
    assert needle in findings[0].message


def test_missing_estate_registry_is_a_config_finding(tmp_path: Path) -> None:
    engine = _engine(
        tmp_path,
        'sources:\n  estate-listings: {plugin: estate-listings, state: "on"}\n',
    )
    ctx = SourceContext(tmp_path, engine.catalog_dir, engine.config, engine.config.sources[0])
    with pytest.raises(CatalogConfigError, match="estate listings not found"):
        EstateListingsSource().listings(ctx)


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
    claude = json.loads(engine.manifests()[CLAUDE_MANIFEST_RELATIVE.as_posix()])
    assert claude["plugins"] == []


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
                _row("no-repo", "extra", repository=None),
                _row("gitlab", "extra", repository="https://gitlab.com/a/b"),
            ]
        )
    )
    written = engine.render(write=True)
    assert set(written) == {CLAUDE_MANIFEST_RELATIVE.as_posix(), CODEX_MANIFEST_RELATIVE.as_posix()}
    claude = json.loads((engine.catalog_dir / CLAUDE_MANIFEST_RELATIVE).read_text(encoding="utf-8"))
    assert claude["name"] == "test-catalog"
    assert claude["owner"] == {"name": "tester"}
    assert [p["name"] for p in claude["plugins"]] == ["mod"]  # module + github repo only
    (plugin,) = claude["plugins"]
    assert plugin["source"] == {"source": "github", "repo": "acme/mod"}
    assert plugin["version"] == "1.0"
    assert plugin["tags"] == ["source:extra", f"trust:{TIER_UNVERIFIED}"]
    codex = json.loads((engine.catalog_dir / CODEX_MANIFEST_RELATIVE).read_text(encoding="utf-8"))
    assert codex == {
        "name": "test-catalog",
        "interface": {"displayName": "Test catalog"},
        "plugins": [],
    }
    assert engine.drift() == []


def test_a_listing_change_without_rerender_is_manifest_drift(tmp_path: Path) -> None:
    engine = _engine(tmp_path, 'sources:\n  extra: {plugin: x, state: "on"}\n')
    source = _CustomSource([_row("one", "extra")])
    engine.sources.register(source)
    engine.render(write=True)
    assert engine.check().ok
    source._rows.append(_row("two", "extra"))
    report = engine.check()
    assert [f.code for f in report.findings] == ["manifest-drift"]
    assert report.findings[0].subject == CLAUDE_MANIFEST_RELATIVE.as_posix()
    assert "stale" in report.findings[0].message


# ---------------------------------------------------------------------------
# the duty + CLI front door
# ---------------------------------------------------------------------------


def test_catalog_is_the_twentieth_duty_and_resolves() -> None:
    assert isinstance(resolve_duty("catalog"), CatalogDuty)
    ns = build_parser().parse_args(["catalog", "render", "--check", "--json"])
    assert (ns.catalog_verb, ns.check, ns.json) == ("render", True, True)
    ns = build_parser().parse_args(["catalog", "--catalog", "/tmp/x"])
    assert (ns.catalog_verb, ns.catalog) == (None, "/tmp/x")


def test_cli_slot_unbound_is_the_only_finding_and_exits_1(tmp_path: Path, capsys) -> None:
    """AC: a new source `on` with `plugin: x` and no plugin `x` registered."""
    catalog_dir = _write_catalog(tmp_path, 'sources:\n  extra: {plugin: x, state: "on"}\n')
    config = load_config(catalog_dir / "catalog.yaml")
    CatalogEngine(tmp_path, config, catalog_dir=catalog_dir).render(write=True)
    rc = main(["catalog", "--catalog", str(catalog_dir), "check", "--json"])
    assert rc == EXIT_FAILED
    payload = json.loads(capsys.readouterr().err)
    assert payload["ok"] is False
    assert [f["code"] for f in payload["findings"]] == ["slot-unbound"]
    assert payload["findings"][0]["subject"] == "sources.extra"
    assert payload["sources"] == [
        {"name": "extra", "plugin": "x", "state": "on", "bound": False, "listings": 0}
    ]
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
    written = json.loads(capsys.readouterr().out)["written"]
    assert all(Path(p).is_file() for p in written)
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


def test_conda_channel_backend_reads_its_declared_options() -> None:
    decl = BackendDecl(name="conda-channel", plugin="conda-channel", state="on", options={})
    assert CondaChannelBackend().snapshot_target(decl) == "conda://SelfExplainML/pyforge-estate-catalog"
    decl = BackendDecl(
        name="conda-channel", plugin="conda-channel", state="on", options={"channel": "c", "package": "p"}
    )
    assert CondaChannelBackend().snapshot_target(decl) == "conda://c/p"


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
    assert payload["count"] == len(rows) == 13
    assert all(r["source"] and r["source"] in declared for r in rows)
    wielded = [r for r in rows if r["source"] == "wielded-suite"]
    assert [r["name"] for r in wielded] == [
        p.name for p in SUITE_PACKAGES if p.install_class == INSTALL_CLASS_MODULE
    ]
    assert {r["trust_tier"] for r in wielded} == {TIER_BMAD_CERTIFIED}
    assert all(r["version"] and r["description"] for r in wielded)  # recipes present
    frames = [r for r in rows if r["source"] == "estate-frames"]
    expected = sorted(
        str(doc.fields["identifier"]).strip() for doc in preflight_frames(root).frames
    )
    assert sorted(r["name"] for r in frames) == expected
    assert len(frames) == 9
    assert {r["kind"] for r in frames} == {KIND_FRAME}


def test_real_tree_claude_manifest_has_the_discovery_shape() -> None:
    manifest = json.loads(
        (default_catalog_dir() / CLAUDE_MANIFEST_RELATIVE).read_text(encoding="utf-8")
    )
    assert manifest["name"] == "pyforge-estate-catalog"
    assert manifest["owner"]["name"] == "rxm7706"
    assert isinstance(manifest["plugins"], list) and manifest["plugins"]
    for plugin in manifest["plugins"]:
        assert plugin["name"]
        assert plugin["source"]["source"] == "github"
        assert plugin["source"]["repo"].count("/") == 1
        assert any(tag.startswith("source:") for tag in plugin["tags"])
        assert any(tag.startswith("trust:") for tag in plugin["tags"])
    codex = json.loads((default_catalog_dir() / CODEX_MANIFEST_RELATIVE).read_text(encoding="utf-8"))
    assert codex["plugins"] == []  # no wielded module ships a .codex-plugin dir


def test_real_tree_estate_registry_is_empty_and_names_its_source() -> None:
    import yaml

    registry = yaml.safe_load(
        (default_catalog_dir() / "registry" / "estate.yaml").read_text(encoding="utf-8")
    )
    assert registry == {"source": "estate-listings", "modules": []}
