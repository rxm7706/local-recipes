"""Steward's dispatcher — and the sole owner of the process exit code (AD-8).

``main()`` catches every way a duty can end and **projects** it to a documented
code. It never trusts a ``SystemExit`` raised inside a duty verbatim, and it
never lets an unexpected exception fall through to the interpreter's bare ``1``
— an undocumented ``1`` is indistinguishable from a duty that legitimately
failed, which is exactly the false signal a gate must not emit.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import __version__
from .interfaces import Duty, DutyResult, NullDuty

EXIT_OK = 0
EXIT_FAILED = 1          # a duty ran and reported ok=False — the ONLY legitimate 1
EXIT_USAGE = 2           # argparse convention
EXIT_INTERRUPTED = 130   # 128 + SIGINT
EXIT_INTERNAL = 70       # EX_SOFTWARE — a crash, never conflated with EXIT_FAILED

# The four duties. `keys` lands first (Epic 1); the rest accept no verbs yet, but
# are declared so `steward --help` states the whole surface from the start.
DUTIES: tuple[str, ...] = ("keys", "deploy", "provision", "budget")

_HELP = {
    "keys": "credential lifecycle — encrypt/decrypt/rotate/list (audit/revoke land in later stories)",
    "deploy": "deployment duties",
    "provision": "environment and substrate provisioning",
    "budget": "cost budgeting and enforcement",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="steward",
        description="Steward — the Provisioner's station.",
    )
    parser.add_argument("--version", action="version", version=f"steward {__version__}")
    subs = parser.add_subparsers(dest="duty", metavar="{" + ",".join(DUTIES) + "}")
    for name in DUTIES:
        duty_parser = subs.add_parser(name, help=_HELP[name], description=_HELP[name])
        if name == "keys":
            _add_keys_subparsers(duty_parser)
    return parser


def _add_keys_subparsers(keys_parser: argparse.ArgumentParser) -> None:
    """Add `encrypt`/`decrypt` verbs (Story 1.3) — the only CLI surface this
    story adds. Flag names deliberately mirror `age`'s own (`--recipient`/
    `-r`, `--identity`/`-i`, `--output`/`-o`).
    """
    keys_subs = keys_parser.add_subparsers(dest="keys_verb", metavar="{encrypt,decrypt,rotate,list}")

    encrypt = keys_subs.add_parser("encrypt", help="age-encrypt a file to a recipient")
    encrypt.add_argument("file", help="the plaintext file to encrypt")
    encrypt.add_argument("--recipient", "-r", required=True, help="the age public key to encrypt to")
    encrypt.add_argument("--output", "-o", required=True, help="path to write the encrypted file")

    decrypt = keys_subs.add_parser("decrypt", help="age-decrypt a file with an identity")
    decrypt.add_argument("file", help="the age-encrypted file to decrypt")
    decrypt.add_argument("--identity", "-i", required=True, help="the age identity (secret key) file")
    decrypt.add_argument("--output", "-o", required=True, help="path to write the decrypted file")

    rotate = keys_subs.add_parser(
        "rotate", help="rotate an issued identity, re-encrypting every secret it protects"
    )
    rotate.add_argument("--scope", required=True, help="the credential scope to rotate")
    rotate.add_argument(
        "--new-identity", required=True, help="path to write the newly generated age identity"
    )
    rotate.add_argument(
        "--inventory",
        default=None,
        help="path to keys-inventory.yaml (default: repo-root .steward/keys-inventory.yaml)",
    )

    list_ = keys_subs.add_parser("list", help="list known credential identities (never a secret value)")
    list_.add_argument(
        "--inventory",
        default=None,
        help="path to keys-inventory.yaml (default: repo-root .steward/keys-inventory.yaml)",
    )
    list_.add_argument("--json", action="store_true", help="emit JSON instead of a text table")


def resolve_duty(name: str) -> Duty:
    """Return the duty implementation for *name*.

    `keys` returns a real `KeysDuty` (Story 1.3); `deploy`/`provision`/
    `budget` are still `NullDuty` — real implementations replace them one
    epic at a time without changing this seam.
    """
    if name == "keys":
        # Imported here, not at module top: keys.py resolves its `_http.py`
        # bridge at import time and refuses to load outside a local-recipes
        # checkout, so a top-level import would take `steward --help`/
        # `--version` and every other duty down with it.
        from .keys import KeysDuty

        return KeysDuty()
    return NullDuty(name)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        parser = build_parser()
        ns = parser.parse_args(argv)
        if not ns.duty:
            parser.print_help()
            return EXIT_OK
        result: DutyResult = resolve_duty(ns.duty).run(ns)
        print(result.summary, file=sys.stderr if not result.ok else sys.stdout)
        return EXIT_OK if result.ok else EXIT_FAILED
    except KeyboardInterrupt:
        print("steward: interrupted", file=sys.stderr)
        return EXIT_INTERRUPTED
    except SystemExit as exc:
        # argparse raises this for --help/--version/usage. Legitimate codes pass
        # through; anything non-int is projected rather than trusted.
        code = exc.code
        if code is None:
            return EXIT_OK
        return code if isinstance(code, int) else EXIT_USAGE
    except Exception:                              # noqa: BLE001 — deliberate boundary
        import traceback
        traceback.print_exc()
        return EXIT_INTERNAL


if __name__ == "__main__":                          # pragma: no cover
    raise SystemExit(main())
