"""Broker vs cache URL helpers (steward 20.2 / canopy AD-10)."""

from __future__ import annotations

from typing import Any


def django_cache_aliases(cache_url: str) -> dict[str, dict[str, Any]]:
    """Django default cache + Wagtail renditions alias on redis-cache."""

    def _alias(key_prefix: str) -> dict[str, Any]:
        return {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": cache_url,
            "KEY_PREFIX": key_prefix,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
            },
        }

    return {
        "default": _alias("django"),
        "renditions": _alias("renditions"),
    }


def channel_layers_for_broker(broker_url: str) -> dict[str, dict[str, Any]]:
    """Channels layer on redis-broker (never redis-cache)."""
    return {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [broker_url]},
        },
    }


def locmem_cache_aliases() -> dict[str, dict[str, Any]]:
    """Process-local caches with distinct LOCATION so renditions stay isolated."""
    return {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "platform-default",
        },
        "renditions": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "platform-renditions",
        },
    }
