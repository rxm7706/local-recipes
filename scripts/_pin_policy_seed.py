#!/usr/bin/env python3
"""One-off helper to build docs/governance/pin-policy.yaml from pixi.toml (Story 100.1 seed)."""
from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

from pin_policy_lib import REPO_ROOT, iter_dependency_decls, _cap_clause, _channel_name, _is_exact_pin

NEVER_MOVE = {
    "conda-libmamba-solver": ("Recipe factory solver pin", "conda-forge-expert", "pyforge-mason"),
    "conda-build": ("Recipe factory build engine", "conda-forge-expert", "pyforge-mason"),
    "conda-index": ("Repodata index generator", "conda-forge-expert", "pyforge-mason"),
    "conda-forge-ci-setup": ("CI fidelity bootstrap", "conda-forge-expert", "pyforge-mason"),
    "conda-forge-pinning": ("Global conda-forge pinning manifest", "conda-forge-expert", "pyforge-mason"),
    "frozendict": ("Immutable dict transitive build dep", "pixi.toml comment", "pyforge-steward"),
    "networkx": ("build_all.py import networkx", "pixi.toml comment", "pyforge-steward"),
    "rattler-build-conda-compat": ("Rattler build compat", "pixi.toml comment", "pyforge-steward"),
    "grayskull": ("Recipe skeleton tool", "conda-forge-expert", "pyforge-mason"),
    "conda-recipe-manager": ("Recipe manager", "conda-forge-expert", "pyforge-mason"),
    "conda-smithy": ("Feedstock tooling", "conda-forge-expert", "pyforge-mason"),
    "shellcheck": ("Shell lint for recipes", "conda-forge-expert", "pyforge-mason"),
    "nodejs": ("Node LTS line policy", "Story 67.1", "pyforge-steward"),
    "python": ("Python 3.14 interpreter pin", "fnd:CAP-12", "pyforge-steward"),
    "django": ("Platform Django family", "platform-dev", "pyforge-steward"),
    "channels": ("Channels stack", "platform-dev", "pyforge-steward"),
    "daphne": ("ASGI server", "platform-dev", "pyforge-steward"),
    "asgiref": ("ASGI utilities", "platform-dev", "pyforge-steward"),
    "channels_redis": ("Channels redis backend", "platform-dev", "pyforge-steward"),
    "wagtail": ("CMS stack", "platform-dev", "pyforge-steward"),
    "coderedcms": ("CodeRed CMS extension", "platform-dev", "pyforge-steward"),
    "postgresql": ("PostgreSQL 17 estate hold", "fnd:CAP-12", "pyforge-steward"),
    "psycopg": ("psycopg cap with PostgreSQL 17", "fnd:CAP-12", "pyforge-steward"),
    "psycopg2": ("psycopg2 cap with PostgreSQL 17", "fnd:CAP-12", "pyforge-steward"),
    "libpq": ("libpq cap with PostgreSQL 17", "fnd:CAP-12", "pyforge-steward"),
    "pgvector": ("pgvector cap with PostgreSQL 17", "fnd:CAP-12", "pyforge-steward"),
    "cachebox": ("Platform policy pin shape", "platform-ci-test", "pyforge-steward"),
    "pixi": ("Workspace pixi floor registry", "CAP-5 pixi-version-check", "pyforge-steward"),
}

POINTER = (
    "Estate pin holds: docs/governance/pin-policy.yaml — "
    "render upgrade: python scripts/pin_policy_check.py --render-command"
)


def main() -> None:
    manifest = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    holds: list[dict] = []
    seen_cap: set[tuple[str, str]] = set()
    seen_channel: set[tuple[str, str]] = set()

    for pkg, (reason, authority, owner) in NEVER_MOVE.items():
        holds.append(
            {
                "package": pkg,
                "hold": "never-move",
                "features": "*",
                "reason": reason,
                "authority": authority,
                "owner": owner,
                "until": "estate refresh policy",
            }
        )

    for d in iter_dependency_decls(manifest):
        if d.has_cap:
            cap = _cap_clause(d.spec)
            key = (d.package, cap or "")
            if key in seen_cap:
                continue
            seen_cap.add(key)
            holds.append(
                {
                    "package": d.package,
                    "hold": "cap",
                    "cap": cap or "<unknown>",
                    "features": [d.feature],
                    "reason": f"Cap preserved across pixi upgrade ({d.feature})",
                    "authority": "spec-100-1",
                    "owner": "pyforge-steward",
                    "until": "unknown",
                }
            )
        if d.has_channel:
            ch = _channel_name(d.raw)
            key = (d.package, ch or "")
            if key in seen_channel:
                continue
            seen_channel.add(key)
            row = {
                "package": d.package,
                "hold": "channel",
                "channel": ch,
                "features": [d.feature],
                "reason": f"Inline channel table ({d.feature})",
                "authority": "spec-100-1",
                "owner": "pyforge-steward",
                "until": "unknown",
            }
            cap = _cap_clause(d.spec)
            if cap:
                row["cap"] = cap
            holds.append(row)
        if d.has_exact:
            holds.append(
                {
                    "package": d.package,
                    "hold": "exact",
                    "exact": d.spec,
                    "features": [d.feature],
                    "reason": f"Exact pin ({d.feature})",
                    "authority": "spec-100-1",
                    "owner": "pyforge-steward",
                    "until": "unknown",
                }
            )

    policy = {
        "version": 1,
        "defaults": {"pinning_strategy": "latest-up", "floors_never_lower": True},
        "pointer": POINTER,
        "holds": holds,
    }
    out = REPO_ROOT / "docs/governance/pin-policy.yaml"
    out.write_text(yaml.dump(policy, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"wrote {out} with {len(holds)} holds")


if __name__ == "__main__":
    main()
