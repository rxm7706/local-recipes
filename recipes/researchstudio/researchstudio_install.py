#!/usr/bin/env python3
"""Copy ResearchStudio skills into a project's .claude/skills/ or .codex/skills/."""
import argparse
import os
import shutil
import sys

BUNDLES = {
    "idea": "ResearchStudio-Idea",
    "reel": "ResearchStudio-Reel",
}


def main():
    parser = argparse.ArgumentParser(
        description="Install ResearchStudio skills into .claude/skills/ (or .codex/skills/)",
        add_help=True,
    )
    parser.add_argument(
        "dest",
        nargs="?",
        default=None,
        help="Destination directory (default: .claude/skills, or .codex/skills with --codex)",
    )
    parser.add_argument("--idea", action="store_true", help="install only the Idea bundle")
    parser.add_argument("--reel", action="store_true", help="install only the Reel bundle")
    parser.add_argument(
        "--codex",
        action="store_true",
        help="default the destination to .codex/skills instead of .claude/skills",
    )
    args = parser.parse_args()

    prefix = os.environ.get("CONDA_PREFIX", "")
    if not prefix:
        print(
            "Error: CONDA_PREFIX is not set. Activate your pixi/conda environment first.",
            file=sys.stderr,
        )
        sys.exit(1)

    root = os.path.join(prefix, "share", "researchstudio")
    if not os.path.isdir(root):
        print(f"Error: researchstudio not found at {root}", file=sys.stderr)
        sys.exit(1)

    # No bundle flag means both.
    wanted = [k for k in ("idea", "reel") if getattr(args, k)] or ["idea", "reel"]

    dest = args.dest
    if dest is None:
        dest = os.path.join(".codex", "skills") if args.codex else os.path.join(".claude", "skills")
    os.makedirs(dest, exist_ok=True)

    installed = []
    for key in wanted:
        source = os.path.join(root, BUNDLES[key], "skills")
        if not os.path.isdir(source):
            print(f"Error: bundle {BUNDLES[key]} not found at {source}", file=sys.stderr)
            sys.exit(1)
        for name in sorted(os.listdir(source)):
            src = os.path.join(source, name)
            if not os.path.isdir(src):
                continue
            dst = os.path.join(dest, name)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            installed.append(name)

    print(f"Installed {len(installed)} skill(s) to '{dest}':")
    for s in installed:
        print(f"  - {s}")
    if not installed:
        print("No skills were installed.", file=sys.stderr)
        sys.exit(1)

    if "idea" in wanted:
        tmpl = os.path.join(root, "ResearchStudio-Idea", ".env.template")
        if os.path.isfile(tmpl):
            print(f"\nResearchStudio-Idea needs connector credentials. Copy and fill in:\n  {tmpl}")


if __name__ == "__main__":
    main()
