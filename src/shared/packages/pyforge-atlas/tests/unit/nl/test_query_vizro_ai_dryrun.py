"""`vizro-ai-dryrun` gate (Story D3, FR-9, AD-7/AD-8, Q3 §11) — BUILD + WIRE ONLY.

Offline, no-network, no-live-LLM gate mirroring the C1 ``dagster-dryrun`` / C2 ``viz-loadable``
/ D2 ``dashboard-dryrun`` pattern. It asserts the buildable-now half of D3 (the live Vizro-AI
NL->chart invocation + the dashboard NL query field are the attended Q3 event, DW-D3):

  * the ``query_vizro_ai`` MCP tool is registered (FastMCP server + audit + package export)
    and callable;
  * with NO backend env configured (the in-container default) the tool returns the structured
    "backend not configured — attended Q3 bring-up (DW-D3)" advisory — no network, no crash,
    no fabricated chart;
  * the backend resolver reads the endpoint from repo model-backend config (env) and a
    configured ``OPENAI_BASE_URL`` is the endpoint used — with NO literal public host baked
    into the resolver source (the Q3 §11 load-bearing invariant);
  * the tool body stays AD-7-thin (only calls the ``_nl`` seam);
  * the NL query is grounded in the D1 BSL models (AD-8), never raw tables/SQL;
  * edge cases degrade rather than crash (partial/malformed config, vizro_ai import failure,
    empty/garbage query, blocked sockets).
"""

from __future__ import annotations

import ast
import re
import socket
import sys
from pathlib import Path

import pytest

from pyforge.atlas import nl
from pyforge.atlas import semantic
from pyforge.atlas.mcp import audit, server, tools
from pyforge.atlas.nl import backend as nl_backend

NL_DIR = Path(nl.__file__).resolve().parent
BACKEND_SRC = (NL_DIR / "backend.py").read_text(encoding="utf-8")
QUERY_SRC = (NL_DIR / "query.py").read_text(encoding="utf-8")

# Public LLM hosts that must NEVER appear baked into the code (Q3 §11).
FORBIDDEN_PUBLIC_HOSTS = (
    "api.openai.com",
    "api.anthropic.com",
    "openai.azure.com",
    "generativelanguage.googleapis.com",
    "api.githubcopilot.com",
    "githubcopilot.com",
)
# A URL literal that carries a HOST (scheme + dotted host) — a bare scheme like "http://" has
# no host and is fine (the resolver validates env values against it).
_URL_WITH_HOST = re.compile(r"https?://[\w.-]+\.\w")

_CFG_ENV = {"OPENAI_BASE_URL": "http://localhost:4141/v1", "OPENAI_API_KEY": "unit-test-key"}


# --------------------------------------------------------------------------- #
# AC-2 — the tool is registered + callable
# --------------------------------------------------------------------------- #


def _mcp_tool_registrations(server_src: str) -> dict[str, str]:
    """Map each ``@mcp.tool()``-decorated function in server.py to the tools.* it delegates
    to. Parsed from source so the assertion does not require the optional FastMCP *server*
    extra AND is immune to the ``tests/mcp`` package shadowing the real ``mcp`` SDK when
    pytest puts ``tests/`` on sys.path (building the live server would import the SDK)."""
    tree = ast.parse(server_src)
    build = next(
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_server"
    )
    reg: dict[str, str] = {}
    for fn in [n for n in ast.walk(build) if isinstance(n, ast.FunctionDef)]:
        decorated = any(
            isinstance(d, ast.Call)
            and isinstance(d.func, ast.Attribute)
            and d.func.attr == "tool"
            for d in fn.decorator_list
        )
        if not decorated:
            continue
        delegate = ""
        for call in (n for n in ast.walk(fn) if isinstance(n, ast.Call)):
            f = call.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "tools":
                delegate = f.attr
        reg[fn.name] = delegate
    return reg


def test_tool_is_registered_in_the_mcp_server_surface():
    """query_vizro_ai is registered in server.py like the other B3 tools (a @mcp.tool()
    wrapper delegating 1:1 to tools.query_vizro_ai)."""
    src = Path(server.__file__).read_text(encoding="utf-8")
    reg = _mcp_tool_registrations(src)
    assert "query_vizro_ai" in reg, f"query_vizro_ai not registered in server.py; got {sorted(reg)}"
    assert reg["query_vizro_ai"] == "query_vizro_ai"
    # exposed alongside the existing surface (sanity: the B3 tools are still there too)
    assert {"read_atlas_dataset", "list_atlas_pipelines"} <= set(reg)


def test_tool_is_exported_and_callable_from_the_package():
    # callable via the tools module AND the package facade (like the other B3 tools)
    assert callable(tools.query_vizro_ai)
    from pyforge.atlas import mcp

    assert callable(mcp.query_vizro_ai)


def test_tool_is_recorded_in_the_audit_as_a_new_nl_capability():
    assert audit.NL_INTERFACE_TOOLS == ("query_vizro_ai",)
    # a NEW capability (no legacy equivalent) — it must not collide with the 23-tool audit
    # nor the pipeline-trigger set.
    assert "query_vizro_ai" not in audit.ATLAS_TOOL_AUDIT
    assert "query_vizro_ai" not in audit.PIPELINE_TRIGGER_TOOLS


# --------------------------------------------------------------------------- #
# AC-1 — unconfigured backend -> structured advisory (no network, no crash, no chart)
# --------------------------------------------------------------------------- #


def test_unconfigured_backend_returns_structured_advisory():
    out = tools.query_vizro_ai("show me the stalest feedstocks", env={})
    assert out["status"] == nl.STATUS_UNCONFIGURED
    assert out["deferred_work"] == "DW-D3"
    assert out["chart"] is None  # live generation deferred — never fabricated
    assert "attended Q3" in out["advisory"]
    assert "bsl_context" in out


def test_unconfigured_is_the_default_with_scrubbed_process_env(monkeypatch):
    for var in ("OPENAI_BASE_URL", "OPENAI_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    out = tools.query_vizro_ai("anything")  # env=None -> reads os.environ
    assert out["status"] == nl.STATUS_UNCONFIGURED
    assert out["chart"] is None


def test_unconfigured_path_makes_no_network_call(monkeypatch):
    """Sockets are hard-blocked; the unconfigured path must still return (no LLM, no net)."""

    def _boom(*a, **k):
        raise AssertionError("no socket may be opened in the unconfigured NL path")

    monkeypatch.setattr(socket, "socket", _boom)
    out = tools.query_vizro_ai("", env={})
    assert out["status"] == nl.STATUS_UNCONFIGURED


# --------------------------------------------------------------------------- #
# AC-3 — resolver reads repo config; configured base-url is the endpoint used; NO hardcoded host
# --------------------------------------------------------------------------- #


def test_resolver_reads_openai_base_url_from_env():
    cfg = nl_backend.resolve_backend(_CFG_ENV)
    assert cfg is not None
    assert cfg.provider == "openai"
    assert cfg.base_url == "http://localhost:4141/v1"  # the configured endpoint, verbatim
    assert cfg.api_key == "unit-test-key"


def test_resolver_reads_anthropic_base_url_from_env():
    cfg = nl_backend.resolve_backend(
        {"ANTHROPIC_BASE_URL": "http://localhost:4141", "ANTHROPIC_API_KEY": "k"}
    )
    assert cfg is not None and cfg.provider == "anthropic"
    assert cfg.base_url == "http://localhost:4141"


def test_configured_backend_uses_the_env_endpoint_and_defers_live_call():
    out = tools.query_vizro_ai("plot downloads", env=_CFG_ENV)
    assert out["status"] == nl.STATUS_DEFERRED
    assert out["endpoint"] == "http://localhost:4141/v1"  # repo-config endpoint, not a default
    assert out["provider"] == "openai"
    assert out["chart"] is None  # live NL->chart is the attended Q3 event
    assert out["deferred_work"] == "DW-D3"


def test_no_hardcoded_public_host_in_the_resolver_or_query_source():
    for label, src in (("backend.py", BACKEND_SRC), ("query.py", QUERY_SRC)):
        for host in FORBIDDEN_PUBLIC_HOSTS:
            assert host not in src, f"hardcoded public host {host!r} found in nl/{label} (Q3 §11)"


@pytest.mark.parametrize("label,src", [("backend.py", BACKEND_SRC), ("query.py", QUERY_SRC)])
def test_nl_source_has_no_url_literal_with_a_host(label, src):
    """Strong Q3 §11 proof: no string constant ANYWHERE in the nl/ endpoint-facing modules
    (backend.py AND query.py) is a host-bearing URL — the endpoint can ONLY come from the
    environment. (Bare schemes like ``http://`` are allowed — they are the validation prefix,
    not an endpoint.) Extended to query.py so a novel provider host baked there — outside the
    fixed FORBIDDEN_PUBLIC_HOSTS enumeration — cannot slip the guard (Reviewer-A NIT)."""
    tree = ast.parse(src)
    offending = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and _URL_WITH_HOST.search(node.value)
    ]
    assert not offending, f"{label} contains hardcoded URL(s) with a host: {offending}"


# --------------------------------------------------------------------------- #
# AC / AD-7 — the tool body stays thin (only delegates to the _nl seam)
# --------------------------------------------------------------------------- #


def _call_root(func: ast.expr) -> str | None:
    node = func
    while True:
        if isinstance(node, ast.Attribute):
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Name):
            return node.id
        else:
            return None


def test_query_vizro_ai_tool_body_is_ad7_thin():
    src = (
        Path(tools.__file__).resolve().parent / "tools.py"
    ).read_text(encoding="utf-8")
    fn = next(
        n for n in ast.parse(src).body
        if isinstance(n, ast.FunctionDef) and n.name == "query_vizro_ai"
    )
    roots = {_call_root(c.func) for c in ast.walk(fn) if isinstance(c, ast.Call)}
    # the ONLY call the body makes is into the nl seam (AD-7: no business logic inline)
    assert roots == {"_nl"}, f"query_vizro_ai body calls beyond the _nl seam: {roots}"


# --------------------------------------------------------------------------- #
# AD-8 — the NL query is grounded in the BSL knowledge graph
# --------------------------------------------------------------------------- #


def test_nl_context_is_grounded_in_the_bsl_models():
    ctx = nl.build_bsl_context("which packages are behind upstream?")
    assert ctx["layer"] == "boring-semantic-layer"
    # models come from the D1 semantic builders (the seam), never hardcoded
    assert ctx["models"] == nl.bsl_model_names()
    assert set(ctx["models"]) >= {"packages", "feedstock_health"}
    # metrics are the declared BSL metric surface (grounding, not raw columns)
    assert ctx["metrics"] == sorted(semantic.METRIC_PROVENANCE)
    assert "is_actionable" in ctx["metrics"]


def test_both_paths_carry_the_bsl_grounding():
    for env in ({}, _CFG_ENV):
        out = tools.query_vizro_ai("q", env=env)
        assert out["bsl_context"]["metrics"] == sorted(semantic.METRIC_PROVENANCE)
        assert out["bsl_context"]["models"] == nl.bsl_model_names()


# --------------------------------------------------------------------------- #
# Reviewer-B edge cases — degrade, never crash
# --------------------------------------------------------------------------- #


def test_partial_config_base_without_key_degrades_to_unconfigured():
    out = tools.query_vizro_ai("q", env={"OPENAI_BASE_URL": "http://localhost:4141/v1"})
    assert out["status"] == nl.STATUS_UNCONFIGURED
    assert "OPENAI_API_KEY is missing" in out["advisory"]


def test_partial_config_key_without_base_degrades_to_unconfigured():
    out = tools.query_vizro_ai("q", env={"OPENAI_API_KEY": "k"})
    assert out["status"] == nl.STATUS_UNCONFIGURED
    assert "OPENAI_BASE_URL is missing" in out["advisory"]


def test_malformed_base_url_degrades_to_unconfigured():
    out = tools.query_vizro_ai("q", env={"OPENAI_BASE_URL": "not-a-url", "OPENAI_API_KEY": "k"})
    assert out["status"] == nl.STATUS_UNCONFIGURED
    assert "not a valid http(s) URL" in out["advisory"]
    assert nl_backend.resolve_backend({"OPENAI_BASE_URL": "not-a-url", "OPENAI_API_KEY": "k"}) is None


@pytest.mark.parametrize("bad_base", ["http://", "https://", "http://   ", "http://\n", "ftp://host"])
def test_scheme_only_or_hostless_base_url_is_not_configured(bad_base):
    """Reviewer-B finding 1: a base-url that is a bare scheme (http://) or lacks a host is NOT a
    usable endpoint — it must degrade to unconfigured, never a false 'configured' receipt that
    only fails at the attended Q3 call. The endpoint still comes only from env; this rejects an
    unroutable value instead of routing to it."""
    assert nl_backend._valid_base_url(bad_base) is False
    env = {"OPENAI_BASE_URL": bad_base, "OPENAI_API_KEY": "k"}
    assert nl_backend.resolve_backend(env) is None
    out = tools.query_vizro_ai("q", env=env)
    assert out["status"] == nl.STATUS_UNCONFIGURED
    assert "not a valid http(s) URL" in out["advisory"]
    # a well-formed host-bearing URL IS accepted (the endpoint comes from env, as required).
    assert nl_backend._valid_base_url("http://localhost:4141/v1") is True


def test_empty_and_garbage_query_still_return_a_structured_advisory():
    for q in ("", "   ", "\x00\x01 asdf ;;; DROP TABLE", "🙂" * 100):
        out = tools.query_vizro_ai(q, env={})
        assert out["status"] == nl.STATUS_UNCONFIGURED
        assert out["query"] == q  # echoed, never executed as SQL/code
        assert out["chart"] is None


def test_vizro_ai_import_failure_never_breaks_the_tool_or_probe(monkeypatch):
    """If ``vizro_ai`` cannot be imported, the guarded probe returns False and the tool still
    returns a structured result (Reviewer-B: a missing/broken vizro_ai must not break D3)."""
    monkeypatch.setitem(sys.modules, "vizro_ai", None)  # any `import vizro_ai` -> ImportError
    assert nl.vizro_ai_available() is False
    out = tools.query_vizro_ai("q", env=_CFG_ENV)
    assert out["status"] == nl.STATUS_DEFERRED
    assert out["vizro_ai_importable"] is False
    assert out["endpoint"] == "http://localhost:4141/v1"


def test_configured_path_makes_no_live_llm_call_even_with_a_backend(monkeypatch):
    """A configured backend must NOT trigger a live call in-container (the live path is the
    attended Q3 event). Block sockets and confirm the configured path still just returns."""

    def _boom(*a, **k):
        raise AssertionError("configured NL path must not open a socket in-container (DW-D3)")

    monkeypatch.setattr(socket, "socket", _boom)
    out = tools.query_vizro_ai("plot it", env=_CFG_ENV)
    assert out["status"] == nl.STATUS_DEFERRED
    assert out["chart"] is None


def test_unconfigured_reason_distinguishes_the_cases():
    assert "no model backend configured" in nl_backend.unconfigured_reason({})
    assert "OPENAI_API_KEY is missing" in nl_backend.unconfigured_reason(
        {"OPENAI_BASE_URL": "http://x.y/v1"}
    )
    assert "not a valid http(s) URL" in nl_backend.unconfigured_reason(
        {"OPENAI_BASE_URL": "garbage"}
    )
