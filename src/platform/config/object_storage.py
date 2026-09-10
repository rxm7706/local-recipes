"""S3-compatible object storage client (Story 50.3; pap:AD-1 dated exception).

`pap:AD-1`'s 2026-09-10 dated exception (see
`spec-pyforge-unifying-strategy/SPEC.md`) permits S3-compatible object storage
as a CONSUMED, never self-hosted, backing service -- the same shape
`canopy:AD-19` already trusts for the external IdP: application config carries
an endpoint URL and credentials only, never a server this platform image
deploys itself. Production target is NetApp StorageGRID, ops-provided and
externally operated.

This module is that consumption seam, and nothing more: one function
resolving a boto3 S3 client from configuration. There is no default endpoint
-- a default here would either point at one specific StorageGRID instance
(forbidden) or make an unconfigured process look configured. The same client
construction works unmodified against Story 50.2's local dev backend
(Silo/Garage, `scripts/platform_object_storage.py`) or a real S3-compatible
endpoint; only the three settings values differ.

No existing feature is wired to consume this seam yet -- that is deliberate,
future, story-by-story work (this story's own scope boundary).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Final

import boto3
from botocore.config import Config
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

__all__ = [
    "ACCESS_KEY_SETTING",
    "ENDPOINT_URL_SETTING",
    "SECRET_KEY_SETTING",
    "object_storage_client",
]

#: Django settings this module resolves from (config/settings/base.py). Named
#: here so a missing-config error can point at the exact setting.
ENDPOINT_URL_SETTING: Final[str] = "OBJECT_STORAGE_ENDPOINT_URL"
ACCESS_KEY_SETTING: Final[str] = "OBJECT_STORAGE_ACCESS_KEY"
SECRET_KEY_SETTING: Final[str] = "OBJECT_STORAGE_SECRET_KEY"  # noqa: S105

#: A placeholder AWS region name, not a real AWS dependency -- boto3 requires
#: some region string even for a non-AWS S3-compatible endpoint, and neither
#: Silo/Garage/MinIO nor StorageGRID attach geographic meaning to it.
_REGION_NAME: Final[str] = "us-east-1"


def _missing_config_message(setting_name: str) -> str:
    return (
        f"{setting_name} is not configured. Object storage consumption "
        "(pap:AD-1's 2026-09-10 dated exception) needs an endpoint URL and "
        "credentials supplied as configuration -- never hardcoded, never a "
        "default pointing at a specific instance. Set the matching env var "
        "(see config/settings/base.py), or run "
        "`pixi run -e platform-object-storage platform-object-storage-up` "
        "for a local dev backend (Story 50.2)."
    )


def object_storage_client() -> S3Client:
    """Return a boto3 S3 client for the configured object-storage endpoint.

    Endpoint and credentials come from Django settings ONLY. The client uses
    path-style addressing -- the form every S3-compatible server (Silo,
    Garage, MinIO, StorageGRID) expects when the endpoint is not a
    wildcard-DNS AWS domain.

    Raises:
        ImproperlyConfigured: any of endpoint URL, access key, or secret key
            is unset.
    """
    endpoint_url = getattr(settings, ENDPOINT_URL_SETTING, None)
    access_key = getattr(settings, ACCESS_KEY_SETTING, None)
    secret_key = getattr(settings, SECRET_KEY_SETTING, None)

    for setting_name, value in (
        (ENDPOINT_URL_SETTING, endpoint_url),
        (ACCESS_KEY_SETTING, access_key),
        (SECRET_KEY_SETTING, secret_key),
    ):
        if not value:
            raise ImproperlyConfigured(_missing_config_message(setting_name))

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=_REGION_NAME,
        config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
    )
