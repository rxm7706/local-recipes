"""Typed refusal for a service assertion that must not yield claims."""


class AssertionRefusedError(Exception):
    """Verifier rejected the token; callers must not use claims."""


class BadSignatureError(AssertionRefusedError):
    """Signature does not match the configured public key."""


class WrongAudienceError(AssertionRefusedError):
    """``aud`` is not the station this verifier serves."""


class ExpiredAssertionError(AssertionRefusedError):
    """``exp`` is in the past."""


class VerifierNotConfiguredError(Exception):
    """OIDC verifier settings are missing or unusable."""


class StationNotInRolesError(AssertionRefusedError):
    """Verified bearer lacks the requested station in roles."""
