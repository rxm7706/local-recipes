"""
With these settings, tests run faster.
"""

from config.authorization.claims import ClaimsContract

from .base import *  # noqa: F403
from .base import TEMPLATES
from .base import env

# isort: split
# After `.base`: its Story 18.1 block puts django-pyforge/src on sys.path when the
# package is not installed. pytest reaches it through the `pythonpath` ini either
# way, but mypy's Django plugin imports this module with a bare interpreter, and
# with these two lines first it died with "No module named django_pyforge".
from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM
from django_pyforge.assertion.golden import GOLDEN_PUBLIC_PEM

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="UJU9GwsVBHxTGOpZqFdxZfnbUirlV3D2XilSEaOyDTYiPpzUx7nYy3SVMFGbekdE",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
# FR-25 / canopy AD-9: ephemeral test DBs keep Django's default migrate on
# create. Do not reuse the Helm Job argv here.
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
OIDC_ALGORITHMS = ["RS256"]
OIDC_LEEWAY_SECONDS = 0.0
# Story 40.1: file:// JWKS is set by assertion tests via fixture; empty here → 503
# unless tests override. platform-ci-test assertion module supplies a test JWKS.
OIDC_JWKS_URL = ""
# Story 18.1 / 19.2: test fixtures, not production station shells.
INSTALLED_APPS = [
    *INSTALLED_APPS,  # noqa: F405
    "django_pyforge.probe_portal",
    "django_pyforge.workclass_probe",
]
# Story 18.3: dedicated assertion golden keys (not local_dev OIDC mint).
PYFORGE_ASSERTION_PRIVATE_KEY = GOLDEN_PRIVATE_PEM
PYFORGE_ASSERTION_PUBLIC_KEY = GOLDEN_PUBLIC_PEM

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Your stuff...
# ------------------------------------------------------------------------------
