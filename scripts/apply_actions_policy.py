#!/usr/bin/env python3
"""Apply `.github/actions-policy.toml` to this repo's GitHub Actions permissions.

One file is the master switch: `enabled = false` turns EVERY workflow off at
the repository permissions layer (Settings → Actions → Disable Actions).
That is the only GitHub control that stops billing without editing each
workflow's `on:` block.

Usage (plain `python`, needs `gh` on PATH, authenticated):
    python scripts/apply_actions_policy.py          # check; exit 1 on drift
    python scripts/apply_actions_policy.py --fix    # PUT live state to match
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_REL = Path(".github") / "actions-policy.toml"
POLICY_PATH = REPO_ROOT / POLICY_REL
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def _gh(args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def _gh_ok(args: list[str], *, input_text: str | None = None) -> str:
    proc = _gh(args, input_text=input_text)
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh {' '.join(args)} failed ({proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()}"
        )
    return proc.stdout


def load_policy(path: Path = POLICY_PATH) -> dict:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    if "enabled" not in data or not isinstance(data["enabled"], bool):
        raise RuntimeError(f"{path}: `enabled` must be a boolean")
    allow = data.get("allow_when_enabled", [])
    if not isinstance(allow, list) or not all(isinstance(x, str) for x in allow):
        raise RuntimeError(f"{path}: `allow_when_enabled` must be a list of strings")
    unknown = [name for name in allow if not (WORKFLOWS_DIR / name).is_file()]
    if unknown:
        raise RuntimeError(
            f"{path}: allow_when_enabled names missing under .github/workflows/: "
            + ", ".join(unknown)
        )
    return {"enabled": data["enabled"], "allow_when_enabled": allow}


def repo_slug() -> str:
    payload = json.loads(_gh_ok(["repo", "view", "--json", "nameWithOwner"]))
    return payload["nameWithOwner"]


def live_enabled(slug: str) -> bool:
    payload = json.loads(_gh_ok(["api", f"repos/{slug}/actions/permissions"]))
    return bool(payload["enabled"])


def set_enabled(slug: str, enabled: bool) -> None:
    body = {"enabled": enabled}
    if enabled:
        body["allowed_actions"] = "all"
    _gh_ok(
        ["api", "--method", "PUT", f"repos/{slug}/actions/permissions", "--input", "-"],
        input_text=json.dumps(body),
    )


def list_workflows(slug: str) -> list[dict]:
    payload = json.loads(
        _gh_ok(
            ["workflow", "list", "--all", "--repo", slug, "--json", "id,name,path,state"]
        )
    )
    return payload


def _workflow_filename(path: str) -> str:
    return Path(path).name


def sync_workflows(slug: str, *, enabled: bool, allow: list[str]) -> list[str]:
    """Disable every disable-able workflow; if enabled, re-enable `allow`."""
    notes: list[str] = []
    allow_set = set(allow) if enabled else set()
    for wf in list_workflows(slug):
        name, state, filename = wf["name"], wf["state"], _workflow_filename(wf["path"])
        want_active = filename in allow_set
        if want_active and state != "active":
            proc = _gh(["workflow", "enable", str(wf["id"]), "--repo", slug])
            if proc.returncode != 0:
                notes.append(f"could not enable {name!r}: {(proc.stderr or '').strip()}")
            else:
                notes.append(f"enabled {name!r}")
            continue
        if not want_active and state == "active":
            proc = _gh(["workflow", "disable", str(wf["id"]), "--repo", slug])
            if proc.returncode != 0:
                notes.append(
                    f"left {name!r} active (cannot disable): {(proc.stderr or '').strip()}"
                )
            else:
                notes.append(f"disabled {name!r}")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check or apply .github/actions-policy.toml to GitHub Actions."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="PUT the live repository to match the policy file",
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="owner/name (default: gh repo view of this checkout)",
    )
    args = parser.parse_args()

    try:
        policy = load_policy()
        slug = args.repo or repo_slug()
        live = live_enabled(slug)
    except (OSError, RuntimeError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        print(f"apply_actions_policy: {exc}", file=sys.stderr)
        return 2

    print(f"policy: {POLICY_REL} enabled={policy['enabled']}")
    print(f"live:   {slug} enabled={live}")
    allow = ", ".join(policy["allow_when_enabled"]) or "(none)"
    print(f"allow_when_enabled: {allow}")

    if live != policy["enabled"]:
        print(
            f"DRIFT: live enabled={live} vs policy enabled={policy['enabled']}",
            file=sys.stderr,
        )
        if not args.fix:
            print("re-run with --fix to apply the policy", file=sys.stderr)
            return 1

    if not args.fix:
        if live == policy["enabled"]:
            print("ok: live master switch matches policy")
        return 0

    if live != policy["enabled"]:
        set_enabled(slug, policy["enabled"])
        print(f"applied master switch enabled={policy['enabled']}")

    for note in sync_workflows(
        slug, enabled=policy["enabled"], allow=policy["allow_when_enabled"]
    ):
        print(f"  {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
