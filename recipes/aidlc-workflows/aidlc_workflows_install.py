#!/usr/bin/env python3
"""Copy an AI-DLC harness distribution tree into the current project."""
import argparse
import os
import shutil
import sys

HARNESSES = ("claude", "kiro", "kiro-ide", "codex")


def main():
    parser = argparse.ArgumentParser(
        description="Install AI-DLC 2.0 workflows into a project directory",
        add_help=True,
    )
    parser.add_argument(
        "--harness",
        choices=HARNESSES,
        default="claude",
        help="Which harness distribution to install (default: claude)",
    )
    parser.add_argument(
        "dest",
        nargs="?",
        default=".",
        help="Target project directory (default: current directory)",
    )
    args = parser.parse_args()

    prefix = os.environ.get("CONDA_PREFIX", "")
    if not prefix:
        print(
            "Error: CONDA_PREFIX is not set. Activate your pixi/conda environment first.",
            file=sys.stderr,
        )
        sys.exit(1)

    source = os.path.join(prefix, "share", "aidlc-workflows", "dist", args.harness)
    if not os.path.isdir(source):
        print(f"Error: harness distribution not found at {source}", file=sys.stderr)
        sys.exit(1)

    dest = args.dest
    os.makedirs(dest, exist_ok=True)

    installed = []
    for name in sorted(os.listdir(source)):
        src = os.path.join(source, name)
        dst = os.path.join(dest, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        installed.append(name)

    print(f"Installed AI-DLC {args.harness} distribution into '{dest}':")
    for s in installed:
        print(f"  - {s}")
    print("NOTE: the workflows' hooks run through bun (https://bun.sh) — install it separately.")
    if not installed:
        print("Nothing was installed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
