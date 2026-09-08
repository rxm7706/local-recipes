"""Story H1 `kedro-test` gate — the 5-persona definitions + their customization-layer
resolution (FR-22(a), § 2.2 / § 7.3).

Proves: the five § 2.2 personas resolve with their mapped BMAD roles/stages/tools; the BMAD
customization layers merge highest-priority-last; and the workforce stays fixed at five (an
overlay may only refine, never add or drop a persona)."""

import pytest

from pyforge.atlas.factory import storage
from pyforge.atlas.factory.personas import (
    DEFAULT_PERSONAS,
    FACTORY_TOOLS,
    PERSONA_NAMES,
    Persona,
    resolve_personas,
)


def test_exactly_the_five_spec_personas():
    assert PERSONA_NAMES == frozenset(
        {"Ingester", "Compiler", "Linker", "Linter", "Oracle"}
    )
    assert set(DEFAULT_PERSONAS) == PERSONA_NAMES


def test_baseline_role_and_stage_mapping():
    # § 2.2 / § 7.3 mapping, verbatim.
    expected = {
        "Ingester": ("Analyst", "raw"),
        "Compiler": ("Architect", "compiled"),
        "Linker": ("Developer", "compiled"),
        "Linter": ("QA/Reviewer", "compiled"),
        "Oracle": ("Product Owner", "outputs"),
    }
    resolved = resolve_personas()
    for name, (role, stage) in expected.items():
        assert resolved[name].role == role
        assert resolved[name].wiki_stage == stage


def test_every_governed_tool_is_a_known_factory_tool():
    for persona in DEFAULT_PERSONAS.values():
        assert set(persona.tools) <= set(FACTORY_TOOLS)
    # The Oracle owns the CMS-push tool (it is the external-interface persona, § 2.2).
    assert "lasuite_client" in DEFAULT_PERSONAS["Oracle"].tools


def test_resolve_with_no_overlays_equals_baseline():
    assert resolve_personas() == DEFAULT_PERSONAS


def test_resolve_does_not_mutate_the_baseline():
    before = DEFAULT_PERSONAS["Linter"].tools
    resolve_personas({"Linter": {"tools": ("search_ops", "pdf_parser")}})
    assert DEFAULT_PERSONAS["Linter"].tools == before


def test_overlay_refines_an_existing_persona():
    resolved = resolve_personas({"Linter": {"tools": ("search_ops", "pdf_parser")}})
    assert resolved["Linter"].tools == ("search_ops", "pdf_parser")
    # Untouched personas are unchanged.
    assert resolved["Oracle"] == DEFAULT_PERSONAS["Oracle"]


def test_higher_customization_layer_wins():
    # Two layers on the same persona: the LATER (higher-priority) layer wins — the CLAUDE.md
    # six-layer "highest priority last" semantics.
    resolved = resolve_personas(
        {"Compiler": {"role": "Analyst"}},  # lower layer
        {"Compiler": {"role": "Developer"}},  # higher layer wins
    )
    assert resolved["Compiler"].role == "Developer"


def test_overlay_naming_unknown_persona_is_rejected():
    # The workforce is fixed at five (§ 2.2): an overlay cannot introduce a sixth agent.
    with pytest.raises(ValueError):
        resolve_personas({"Auditor": {"role": "QA/Reviewer"}})


def test_overlay_may_not_rename_a_persona():
    # A persona's name is its identity (and registry key); an overlay renaming it would decouple
    # the key from `.name` and could make two personas report the same name.
    with pytest.raises(ValueError):
        resolve_personas({"Oracle": {"name": "Ingester"}})
    # A no-op name override that MATCHES the key is harmless (still refines other fields).
    resolved = resolve_personas({"Oracle": {"name": "Oracle", "wiki_stage": "compiled"}})
    assert resolved["Oracle"].name == "Oracle"
    assert resolved["Oracle"].wiki_stage == "compiled"


def test_overlay_with_bad_field_fails_loudly_at_resolution():
    # A merged persona with an out-of-vocab tool must fail at resolve time, not first use.
    with pytest.raises(ValueError):
        resolve_personas({"Ingester": {"tools": ("nonexistent_tool",)}})


def test_resolution_always_returns_five():
    resolved = resolve_personas({"Oracle": {"wiki_stage": "compiled"}})
    assert set(resolved) == PERSONA_NAMES
    assert all(isinstance(p, Persona) for p in resolved.values())


# --- storage backend resolution (§ 7.4, AD-16/AD-22) ------------------------------------


def test_storage_defaults_to_offline_filesystem(monkeypatch):
    # No endpoint env => the offline filesystem default (MinIO server is DEFERRED, DW-H1).
    for var in (
        storage.WIKI_S3_ENDPOINT_ENV,
        storage.WIKI_S3_BUCKET_ENV,
        storage.WIKI_S3_ACCESS_KEY_ENV,
        storage.WIKI_S3_SECRET_KEY_ENV,
    ):
        monkeypatch.delenv(var, raising=False)
    cfg = storage.resolve_storage_config()
    assert cfg.backend == "filesystem"
    assert cfg.endpoint == "" and cfg.has_credentials is False


def test_empty_endpoint_env_is_treated_as_unset(monkeypatch):
    monkeypatch.setenv(storage.WIKI_S3_ENDPOINT_ENV, "")
    assert storage.resolve_storage_config().backend == "filesystem"


def test_configured_endpoint_selects_minio_without_hardcoding_host(monkeypatch):
    monkeypatch.setenv(storage.WIKI_S3_ENDPOINT_ENV, "minio.internal:9000")
    monkeypatch.setenv(storage.WIKI_S3_BUCKET_ENV, "atlas-wiki")
    monkeypatch.setenv(storage.WIKI_S3_ACCESS_KEY_ENV, "ak")
    monkeypatch.setenv(storage.WIKI_S3_SECRET_KEY_ENV, "sk")
    cfg = storage.resolve_storage_config()
    assert cfg.backend == "minio"
    assert cfg.endpoint == "minio.internal:9000"
    assert cfg.bucket == "atlas-wiki"
    assert cfg.has_credentials is True


def test_minio_without_both_keys_reports_no_credentials(monkeypatch):
    monkeypatch.setenv(storage.WIKI_S3_ENDPOINT_ENV, "minio.internal:9000")
    monkeypatch.setenv(storage.WIKI_S3_ACCESS_KEY_ENV, "ak")
    monkeypatch.delenv(storage.WIKI_S3_SECRET_KEY_ENV, raising=False)
    assert storage.resolve_storage_config().has_credentials is False
