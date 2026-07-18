#!/usr/bin/env python3
"""Copy andrej-karpathy-skills into the current project's .claude/skills/ directory."""
import argparse
import os
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Install andrej-karpathy-skills into .claude/skills/",
        add_help=True,
    )
    parser.add_argument(
        "dest",
        nargs="?",
        default=os.path.join(".claude", "skills"),
        help="Destination directory (default: .claude/skills)",
    )
    args = parser.parse_args()

    # sys.prefix always points at the running interpreter's env root
    # (CONDA_PREFIX is unset in some subshells/IDE launches).
    prefix = sys.prefix

    source = os.path.join(prefix, "share", "andrej-karpathy-skills", "skills")
    if not os.path.isdir(source):
        print(f"Error: andrej-karpathy-skills not found at {source}", file=sys.stderr)
        sys.exit(1)

    dest = args.dest
    os.makedirs(dest, exist_ok=True)

    installed = []
    for name in sorted(os.listdir(source)):
        src = os.path.join(source, name)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(dest, name)
        if os.path.lexists(dst):
            if os.path.isdir(dst) and not os.path.islink(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
        shutil.copytree(src, dst)
        installed.append(name)

    print(f"Installed {len(installed)} skill(s) to '{dest}':")
    for s in installed:
        print(f"  - {s}")
    if not installed:
        print("No skills were installed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
