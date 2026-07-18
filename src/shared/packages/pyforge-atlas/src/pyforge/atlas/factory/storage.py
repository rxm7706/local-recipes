"""Wiki storage-backend resolution — env-driven, offline by default (Story H1, § 7.4, AD-16/AD-22).

The Karpathy wiki is backed by MinIO (S3) + PostgreSQL "both provisioned from conda-forge per
FR-15" (§ 7.4). Two facts shape this module:

* **Only the MinIO *Python SDK* is in-env today; the MinIO *server* is NOT provisioned** — that
  server bring-up is the H1 precondition the architecture records as Deferred (see DW-H1). So the
  factory must run with NO server present: the default backend is the plain **local filesystem**
  (the scaffolded ``wiki/`` tree), fully offline. A MinIO backend is selected ONLY when an
  endpoint is explicitly configured via env.
* **Host-agnostic (AD-2/AD-16).** No endpoint, bucket, or credential is hardcoded. Which host
  backs the wiki (a local dir, or a conda-forge MinIO / enterprise S3 mirror) is a deploy-time
  env choice resolved HERE, mirroring ``settings._env_or`` for the catalog endpoint bases.

Selecting the MinIO backend does not open a connection — this module only RESOLVES config; the
live client + server bring-up is the attended deferral.
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict

#: Env var whose presence flips the backend from local-filesystem to MinIO/S3. Empty/unset =>
#: filesystem (the offline default). Named, never a hardcoded host (AD-2).
WIKI_S3_ENDPOINT_ENV = "ATLAS_WIKI_S3_ENDPOINT"
WIKI_S3_BUCKET_ENV = "ATLAS_WIKI_S3_BUCKET"
WIKI_S3_ACCESS_KEY_ENV = "ATLAS_WIKI_S3_ACCESS_KEY"
WIKI_S3_SECRET_KEY_ENV = "ATLAS_WIKI_S3_SECRET_KEY"


class WikiStorageConfig(BaseModel):
    """The resolved wiki storage target — immutable, no unknown fields.

    ``backend == "filesystem"`` (the default) means the local ``wiki/`` tree; ``"minio"`` means
    an S3-compatible object store at ``endpoint``/``bucket``. Whether credentials are present is
    exposed via :attr:`has_credentials` WITHOUT leaking the secret into the model (the secret is
    read from env at client-build time by the deferred live bring-up, never stored here)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    backend: Literal["filesystem", "minio"]
    endpoint: str = ""
    bucket: str = ""
    has_credentials: bool = False


def _env_or(var: str, default: str = "") -> str:
    """Return ``$var`` unless empty/unset, mirroring ``settings._env_or`` (an EMPTY env var is
    treated as UNSET, not as an empty endpoint) — one resolution convention across the project."""
    val = os.environ.get(var)
    return val if val else default


def resolve_storage_config() -> WikiStorageConfig:
    """Resolve the wiki storage backend from the environment.

    No :data:`WIKI_S3_ENDPOINT_ENV` (or an empty one) => the offline **filesystem** default (the
    scaffolded ``wiki/`` tree; no server needed). A configured endpoint => the **minio** backend,
    carrying its endpoint/bucket and whether BOTH access+secret keys are present. This resolves
    config only; it opens no connection (the live client is the deferred H1 bring-up)."""
    endpoint = _env_or(WIKI_S3_ENDPOINT_ENV)
    if not endpoint:
        return WikiStorageConfig(backend="filesystem")
    return WikiStorageConfig(
        backend="minio",
        endpoint=endpoint,
        bucket=_env_or(WIKI_S3_BUCKET_ENV),
        has_credentials=bool(
            _env_or(WIKI_S3_ACCESS_KEY_ENV) and _env_or(WIKI_S3_SECRET_KEY_ENV)
        ),
    )
