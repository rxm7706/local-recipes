#!/usr/bin/env python3
"""bump-pixi-version — rewrite every registered pixi-version pin site to one
target version, in one pass.

Companion mutator to `scripts/pixi_version_check.py` (the detector); both
read the same registry in `scripts/pixi_version_registry.py`, so there is
never a second, drifting list of "everywhere pixi is pinned." Run this
instead of hand-editing sites one at a time -- that is exactly how
`src/platform/compose/dbgpt/Containerfile` went unnoticed on 2026-08-21
(a real `pixi upgrade` moved pixi.toml's own floors; nothing moved the 10
external sites, and one of them was not even registered in the hand-kept
enumeration this registry replaces).

Steps, in order:
  1. Best-effort verify the target `ghcr.io/prefix-dev/pixi:<version>` image
     tag actually exists on ghcr.io (anonymous token pull check) -- warns and
     continues on any network failure, since some environments have no
     egress; never silently skips a REAL 404, which fails loud.
  2. Rewrite every non-derived site via its registered regex, asserting the
     expected hit count so a site that gained or lost a pin is a hard error,
     not a silent partial rewrite.
  3. Regenerate environment.yaml with the real generator
     (`pixi project export conda-environment -e build`) rather than
     regex-patching a DERIVED file.
  4. Re-run the check to confirm convergence.

Exits non-zero on any site whose hit count doesn't match the registry, or if
the post-bump check still finds drift -- this must never report success on a
partial rewrite.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import urllib.error
import urllib.request

from pixi_version_registry import REPO_ROOT, SITES, master_version


def verify_image_exists(version: str) -> bool | None:
    """True/False if reachable, None if the check itself could not run
    (no network) -- callers must treat None as "unverified," not "failed.\""""
    try:
        token_req = urllib.request.Request(
            "https://ghcr.io/token?scope=repository:prefix-dev/pixi:pull")
        with urllib.request.urlopen(token_req, timeout=10) as resp:
            import json as _json
            token = _json.load(resp)["token"]
        req = urllib.request.Request(
            f"https://ghcr.io/v2/prefix-dev/pixi/manifests/{version}",
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.oci.image.index.v1+json"},
            method="HEAD",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as exc:
        return exc.code == 200
    except Exception:
        return None


def bump(version: str) -> int:
    exists = verify_image_exists(version)
    if exists is False:
        print(f"REFUSING: ghcr.io/prefix-dev/pixi:{version} does not exist "
              f"(checked ghcr.io directly). Pass a real released pixi version.",
              file=sys.stderr)
        return 2
    if exists is None:
        print(f"warning: could not verify ghcr.io/prefix-dev/pixi:{version} exists "
              f"(no network reach from here) -- proceeding unverified.", file=sys.stderr)

    changed: list[str] = []
    for site in SITES:
        if site.derived:
            continue
        if not site.path.is_file():
            print(f"ABORT: {site.name} — {site.path} does not exist", file=sys.stderr)
            return 2
        text = site.path.read_text(encoding="utf-8")
        matches = list(site.pattern.finditer(text))
        if len(matches) != site.expected_hits:
            print(f"ABORT: {site.name} — expected {site.expected_hits} pin(s) in "
                  f"{site.path}, found {len(matches)}. Registry may be stale; "
                  f"fix scripts/pixi_version_registry.py before retrying.",
                  file=sys.stderr)
            return 2

        def _replace(m: re.Match[str]) -> str:
            return m.group(0).replace(m.group(1), version)

        new_text, n = site.pattern.subn(_replace, text)
        if n != site.expected_hits:
            print(f"ABORT: {site.name} — rewrite touched {n} occurrence(s), "
                  f"expected {site.expected_hits}", file=sys.stderr)
            return 2
        if new_text != text:
            site.path.write_text(new_text, encoding="utf-8")
            changed.append(site.name)

    print(f"rewrote {len(changed)} site(s) to {version}:")
    for name in changed:
        print(f"  - {name}")

    env_site = next(s for s in SITES if s.derived)
    print(f"\nregenerating {env_site.path.relative_to(REPO_ROOT)} "
          f"(pixi project export conda-environment -e build)...")
    with env_site.path.open("w", encoding="utf-8") as fh:
        result = subprocess.run(
            ["pixi", "project", "export", "conda-environment", "-e", "build"],
            cwd=REPO_ROOT, stdout=fh, stderr=subprocess.PIPE, text=True, timeout=60,
        )
    if result.returncode != 0:
        print(f"ABORT: environment.yaml export failed:\n{result.stderr}", file=sys.stderr)
        return 2

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="bump-pixi-version",
        description="Rewrite every registered pixi-version pin site (pixi.toml, CI "
                    "workflows, both Containerfiles, environment.yaml) to one target "
                    "version in a single pass.")
    parser.add_argument("version", nargs="?",
                         help="target version, e.g. 0.78.0. Defaults to pixi.toml's "
                              "current requires-pixi floor (use this to re-converge "
                              "sites after fixing an unregistered one by hand).")
    args = parser.parse_args()

    version = args.version or master_version()
    rc = bump(version)
    if rc != 0:
        return rc

    print("\nre-checking...")
    check = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "pixi_version_check.py")],
        cwd=REPO_ROOT,
    )
    return check.returncode


if __name__ == "__main__":
    sys.exit(main())
