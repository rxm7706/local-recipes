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
    cap_feats: dict[tuple[str, str], set[str]] = {}
    channel_feats: dict[tuple[str, str], tuple[dict, set[str]]] = {}
    exact_rows: list[dict] = []

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
        if d.has_cap and not d.has_channel:
            cap = _cap_clause(d.spec) or "<unknown>"
            cap_feats.setdefault((d.package, cap), set()).add(d.feature)
        if d.has_channel:
            ch = _channel_name(d.raw) or ""
            cap = _cap_clause(d.spec)
            key = (d.package, ch)
            row_template = {"channel": ch}
            if cap:
                row_template["cap"] = cap
            if key not in channel_feats:
                channel_feats[key] = (row_template, set())
            channel_feats[key][1].add(d.feature)
        if d.has_exact:
            ver = d.spec
            if isinstance(d.raw, dict) and "version" in d.raw:
                ver = str(d.raw["version"])
            exact_rows.append(
                {
                    "package": d.package,
                    "hold": "exact",
                    "exact": ver,
                    "features": [d.feature],
                    "reason": f"Exact pin ({d.feature})",
                    "authority": "spec-100-1",
                    "owner": "pyforge-steward",
                    "until": "unknown",
                }
            )

    for (pkg, cap), feats in sorted(cap_feats.items()):
        holds.append(
            {
                "package": pkg,
                "hold": "cap",
                "cap": cap,
                "features": sorted(feats),
                "reason": "Cap preserved across pixi upgrade",
                "authority": "spec-100-1",
                "owner": "pyforge-steward",
                "until": "unknown",
            }
        )
    for (pkg, ch), (template, feats) in sorted(channel_feats.items()):
        row = {
            "package": pkg,
            "hold": "channel",
            "channel": template["channel"],
            "features": sorted(feats),
            "reason": "Inline channel table preserved across pixi upgrade",
            "authority": "spec-100-1",
            "owner": "pyforge-steward",
            "until": "unknown",
        }
        if "cap" in template:
            row["cap"] = template["cap"]
        holds.append(row)
    holds.extend(exact_rows)

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
