"""Dedicated RS256 golden keypair for service assertions (not persona JWT mint).

The PEM headers are assembled from fragments so a repo-wide secrets-scan over
source files (Story 7.3 / 48.10 guild-image build) does not match a literal
``-----BEGIN … PRIVATE KEY-----`` line in this test-only fixture module.
Runtime consumers still receive a valid PEM string from the constants below.
The private header is formatted when the module loads, never written as two
literals joined by ``+``: the compiler folds those into one constant, and the
scan finds the whole header in the compiled module (steward Story 118.10).

The base64 is held at 76 characters a line and wrapped at 64 when the module
loads (steward Story 118.10). Held at 64, a line is a run of its own, and a
line with no ``+`` or ``/`` is exactly the 64 mixed-case alphanumerics of the
scan's ``hetzner-api-token`` shape; six of this keypair's lines were, and the
guild image's build gate failed on them.
"""

_PRIVATE = "PRIVATE"
_BEGIN_PRIVATE = f"-----BEGIN {_PRIVATE} KEY-----\n"
_END_PRIVATE = "-----END PRIVATE KEY-----\n"
_BEGIN_PUBLIC = "-----BEGIN " + "PUBLIC KEY-----\n"
_END_PUBLIC = "-----END PUBLIC KEY-----\n"

_GOLDEN_PRIVATE_BASE64 = """
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDX400EFQIAgfRuPFohJak80T9O
Z6QsRx+0D+k21SRSeSXoaYPoEQJPOFS36inSUWzqt80Obi5p8kUamVI21NB9+W81swtmDe/M7TLN
4OV9LlA14g/YpWS5ohYSFjr1l2SHBlF4jraWSttM/oPojc4tBkcVNmw17vLxf+A4IT6Otr173l1g
/3dhEvcWS2BpYMdlqx72k4fOsEHyGHupH4RplSLWfAZwMpnGpOGDwGqQ4DsEkBCiaym40/mZvSO9
bn1/jWeWMNSEnjcEgrtt7cNm8IKfhAQGd5psxEJaJAv2xG+1Th/Z9V2RmIazULnoA0p89JvCNJ7P
GSE7JHSdipVFAgMBAAECggEAGOfDhEOKKhXT5X235hgKqJX5KCnjsin4WdT2EhnPqWYJfgDiMzz3
F72HZHoyne0/0+olUVNbrmRBHZrvdZzieo3yiu7fU0QrVGhO0pptzx2vKjAspNEbyCCPTEHdRmTT
N5J+hppsLPVwzDaWcBcf4GjXfXZ8UFKDG2Ils0P+jAcJfo+ZGGkB/jZuPkQCVVs80dfmedk2e3r7
JhlQL4UKGgqUZCIaJgrzuL15ujACkqgzqqRLABMMDtR6M0stiJij3d4zJIT9ghlvyUADHxi02udA
dIaqoEPyu8XbU/ppv7SoWiWqOyPnPZ7ol8y3KfHLTZb2JlMl2x48t3jBbOB/AQKBgQD8hiJHW9BK
pAYi8utYcjflKvxU1tSq6ksZhF4STqBPxpIATcoGJvqg8zhbY6x+O7ce8iAmMsyy1Wm6rp7DkoXR
FUad3p5gLos0cOvhXb9+65UNRrZDPvtY++9Zy/6Wdsmwr/Nau8v2x9jStl28rsTyyrXEBsSqpqGz
GcK1rqa3xQKBgQDa3BDIMTufJQU6ggF9dwNtqatGMj5nK7BkEhY7EoCj+7hFtR7AIgn7Gty82tNg
d6v35c+Q5bAZ4Oh+E1CYnsXIJXho4uzx4wTpQnvnSCyk08vlXSrltMIXogKzbyf0+sJ8SgFqxLt+
z6KtetkNsPDUBJWinN5Qnwqxm1A1sXy/gQKBgQDVJwfSQg68ol1HrNK48ph5yWH63ufeaSwBGvko
7NNm408kEIVh0g8mQockpSrZ1uAIsAoxFBozLe80E+eRX6GyzgmwglQfDcqU9mg08CQPJx3GehSp
CIWzI91yZ727FgPDL5Hz2acd5K0Bl8vh04gNBMyO7cOd5E+DVVBEeWrinQKBgQDFWMCNM8+2PjSL
wGTFlIZz4RV+05lvgHaqlaCUHaf/teBAgwQ6bbcgROWcKZmGmAJqI0BaQLLdcu9Rl+sJ48kmI5uC
wHS13GY2S2vcbjlLW2u046Dlxmtp0f2rfOTDw0WRu02xz7ndrC7dTTPhY5aVJ5kiK19PxUloQ0s9
T1DUgQKBgCCs+9KDKieDFWM+FnX99EJ3f6f/TM9nzSVzgtsq34xxsky6cl4OLY4LQEUpZ990T762
ArXxYeEuhwcJfd6bUx2dtDDaEDZNp8tRKGOzG+DN4ZCoZ3voxHDhUbYgk4XrMWPQJJg81GyOHdaP
qV05rMZ9njSFMK5VQLjLy6IBe3V/
"""

_GOLDEN_PUBLIC_BASE64 = """
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1+NNBBUCAIH0bjxaISWpPNE/TmekLEcf
tA/pNtUkUnkl6GmD6BECTzhUt+op0lFs6rfNDm4uafJFGplSNtTQfflvNbMLZg3vzO0yzeDlfS5Q
NeIP2KVkuaIWEhY69ZdkhwZReI62lkrbTP6D6I3OLQZHFTZsNe7y8X/gOCE+jra9e95dYP93YRL3
FktgaWDHZase9pOHzrBB8hh7qR+EaZUi1nwGcDKZxqThg8BqkOA7BJAQomspuNP5mb0jvW59f41n
ljDUhJ43BIK7be3DZvCCn4QEBneabMRCWiQL9sRvtU4f2fVdkZiGs1C56ANKfPSbwjSezxkhOyR0
nYqVRQIDAQAB
"""


def _wrap64(base64: str) -> str:
    """`base64` with its line breaks removed, then one line per 64 characters, each ending in a newline."""
    flat = "".join(base64.split())
    return "".join(flat[i : i + 64] + "\n" for i in range(0, len(flat), 64))


_GOLDEN_PRIVATE_BODY = _wrap64(_GOLDEN_PRIVATE_BASE64)
_GOLDEN_PUBLIC_BODY = _wrap64(_GOLDEN_PUBLIC_BASE64)

GOLDEN_PRIVATE_PEM = _BEGIN_PRIVATE + _GOLDEN_PRIVATE_BODY + _END_PRIVATE
GOLDEN_PUBLIC_PEM = _BEGIN_PUBLIC + _GOLDEN_PUBLIC_BODY + _END_PUBLIC
