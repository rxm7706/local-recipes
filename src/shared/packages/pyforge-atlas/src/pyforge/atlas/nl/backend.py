"""LLM backend resolution from REPO model-backend configuration (Story D3, FR-9, Q3 §11).

The Q3 §11 default is BINDING: the NL interface's LLM backend is resolved from the repo's
model-backend configuration — env-var driven — and NEVER from a hardcoded public endpoint.
This module reads the OpenAI-compatible / Anthropic base-url + key convention documented in
``docs/copilot-to-api.md`` (§ "Ad-hoc Python scripts": scripts read ``OPENAI_BASE_URL`` /
``OPENAI_API_KEY`` and the Anthropic equivalents from the environment) and returns a resolved
:class:`BackendConfig` or ``None``.

Load-bearing invariant: there is NO literal provider host (no public LLM endpoint) anywhere
in this file — the endpoint always comes from the environment. The ``vizro-ai-dryrun`` gate
asserts this by scanning the source for any host-bearing URL literal.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlparse

# The env-var convention (docs/copilot-to-api.md). Each provider needs BOTH a base-url and a
# key to be considered configured — a partial config degrades to "unconfigured" (never a
# guessed/public default). The optional model override is read but not required.
_OPENAI_BASE = "OPENAI_BASE_URL"
_OPENAI_KEY = "OPENAI_API_KEY"
_ANTHROPIC_BASE = "ANTHROPIC_BASE_URL"
_ANTHROPIC_KEY = "ANTHROPIC_API_KEY"
_MODEL_OVERRIDE = "VIZRO_AI_MODEL"


@dataclass(frozen=True)
class BackendConfig:
    """A resolved model backend — the endpoint + key come from the environment, never code."""

    provider: str          # "openai" (OpenAI-compatible) | "anthropic"
    base_url: str          # resolved from the *_BASE_URL env var
    api_key: str           # resolved from the *_API_KEY env var
    model: str | None      # optional VIZRO_AI_MODEL override


def _valid_base_url(value: str | None) -> bool:
    """A configured endpoint must be an http(s) URL WITH A HOST. A bare scheme
    (``http://``, ``http://  ``) is NOT a usable endpoint — accepting it would mark a
    typo'd env var as "configured" and hand out a false receipt that only fails at the
    attended Q3 call (Reviewer-B finding 1). The host still comes only from env; this just
    rejects an unroutable value instead of routing to it."""
    if not value:
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def resolve_backend(env: Mapping[str, str] | None = None) -> BackendConfig | None:
    """Resolve the LLM backend from repo model-backend config (env), or ``None`` if unset.

    OpenAI-compatible config wins when present (the repo's bridge default — a local
    OpenAI-compatible base-url, ``docs/copilot-to-api.md``); the Anthropic pair is the
    fallback. A provider is "configured" only when its base-url is a well-formed URL AND its
    key is non-empty; anything else (unset, partial, malformed) resolves to ``None`` so the
    caller degrades to the structured advisory rather than routing anywhere.
    """
    env = os.environ if env is None else env
    model = (env.get(_MODEL_OVERRIDE) or "").strip() or None

    base = env.get(_OPENAI_BASE)
    key = env.get(_OPENAI_KEY)
    if _valid_base_url(base) and (key or "").strip():
        return BackendConfig("openai", base.strip(), key.strip(), model)

    abase = env.get(_ANTHROPIC_BASE)
    akey = env.get(_ANTHROPIC_KEY)
    if _valid_base_url(abase) and (akey or "").strip():
        return BackendConfig("anthropic", abase.strip(), akey.strip(), model)

    return None


def unconfigured_reason(env: Mapping[str, str] | None = None) -> str:
    """A human/agent-readable reason the backend did not resolve — surfaced in the advisory.

    Distinguishes "nothing set" from a PARTIAL config (base-url without key, or vice versa)
    and a MALFORMED base-url, so an operator bringing the Q3 backend up sees exactly what is
    missing without the tool ever guessing a default.
    """
    env = os.environ if env is None else env
    for base_var, key_var in ((_OPENAI_BASE, _OPENAI_KEY), (_ANTHROPIC_BASE, _ANTHROPIC_KEY)):
        base = env.get(base_var)
        key = env.get(key_var)
        if base and not _valid_base_url(base):
            return f"{base_var} is set but is not a valid http(s) URL"
        if base and not (key or "").strip():
            return f"{base_var} is set but {key_var} is missing"
        if (key or "").strip() and not base:
            return f"{key_var} is set but {base_var} is missing"
    return (
        f"no model backend configured (set {_OPENAI_BASE}+{_OPENAI_KEY} or "
        f"{_ANTHROPIC_BASE}+{_ANTHROPIC_KEY} — repo model-backend routing, never a public endpoint)"
    )
