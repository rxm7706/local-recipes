"""
With these settings, tests run faster.
"""

from config.authorization.claims import ClaimsContract

from .base import *  # noqa: F403
from .base import TEMPLATES
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="UJU9GwsVBHxTGOpZqFdxZfnbUirlV3D2XilSEaOyDTYiPpzUx7nYy3SVMFGbekdE",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# DEBUGGING FOR TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore[index]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "http://media.testserver/"

# CAP-1 / steward 16.5: configured claims contract for OIDC mapper tests.
CLAIMS_CONTRACT = ClaimsContract(
    identity_key_claim="sub",
    group_claim="groups",
    staff_group="platform-staff",
    superuser_group="platform-superuser",
)
OIDC_ISSUER = "https://test.invalid/realms/platform"
OIDC_AUDIENCE = "platform-web"
# Story 18.1: second portal is a test fixture, not an Epic 19 shell.
INSTALLED_APPS = [*INSTALLED_APPS, "django_pyforge.probe_portal"]  # noqa: F405

# Your stuff...
# ------------------------------------------------------------------------------
