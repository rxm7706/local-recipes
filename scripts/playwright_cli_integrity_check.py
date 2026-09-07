#!/usr/bin/env python3
"""playwright-cli-integrity-check — catch the Playwright CLI clobber.

`playwright-python` DEPENDS on the Node `playwright` package, so any
environment carrying the Python bindings has both installed, and both want
to own `bin/playwright`:

    playwright         (Node)   bin/playwright -> ../lib/node_modules/playwright/cli.js   [symlink]
    playwright-python  (Python) bin/playwright                                            [regular file]

When the Python console script is written to that path while the Node
package's symlink is still there, the write follows the symlink and lands
*inside* `cli.js`. Because conda hardlinks package files from the shared
package cache into every environment, that single write corrupts the CACHE
entry, and the damage then propagates to every environment on the machine
that links the same build.

Observed on this machine 2026-09-07: nine poisoned copies (two 1.63.0 cache
builds, two 1.62.1 cache builds, five pixi envs). `cli.js` contained a
Python console script whose interpreter path pointed into a DELETED
`.claude/worktrees/agent-*` env, so the Node CLI failed with a
`SyntaxError` months after the fact and `bin/playwright` was missing
outright -- BOTH CLIs broken, with no error at install time.

It is a race, not a certainty: a fresh `mamba create` into a clean cache
links it correctly. That is exactly why it needs a detector rather than a
fix -- it fails silently, survives for months, and is invisible until
something tries to run the CLI.

What this checks, per environment and per cached package build:

    (a) cli-clobbered     lib/node_modules/playwright/cli.js must be the Node
                          shim (`#!/usr/bin/env node`). A `'''exec'` line, or
                          any Python source, means the write-through happened.

    (b) cli-dangling-interp
                          a clobbered cli.js usually names an interpreter that
                          no longer exists; reported separately because it
                          tells the operator the corruption is OLD and the
                          originating env is gone.

    (c) bin-missing       an environment with playwright-python installed must
                          expose `bin/playwright`. Its absence is the other
                          half of the same event: the console script's content
                          went into cli.js instead of its own file.

    (d) bin-is-symlink    `bin/playwright` must be a regular file, never a
                          symlink into node_modules. A symlink there is the
                          loaded gun -- it is what makes the next write
                          corrupt cli.js instead of simply replacing a file.

Scope is `runtime`: it reads installed environments and the rattler package
cache, never tracked files.

Exit codes: 0 clean (including "nothing installed to check"), 1 findings,
2 could-not-run.

Repair (what was done by hand on 2026-09-07, for reference):
  * restore cli.js by TRUNCATING IN PLACE (`cat pristine > cli.js`) rather
    than unlink+write -- truncating preserves the inode, so every hardlinked
    copy across the cache and all envs is repaired by one write. Unlinking
    would fix one path and strand the rest on the old, still-poisoned inode.
  * recreate `bin/playwright` as a REGULAR FILE (the playwright-python
    console script with that env's own interpreter), never as the Node
    symlink -- a regular file cannot be written *through*.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

DETECTOR = {"scope": "runtime"}

NODE_SHEBANG = "#!/usr/bin/env node"
CLI_REL = pathlib.Path("lib/node_modules/playwright/cli.js")


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


def _candidate_roots(repo: pathlib.Path) -> list[tuple[str, pathlib.Path]]:
    """Every prefix that could carry a playwright install.

    Environments and cached package builds are both included: repairing only
    the environments leaves the cache poisoned, and the next link pulls the
    corruption straight back in.
    """
    roots: list[tuple[str, pathlib.Path]] = []
    envs = repo / ".pixi" / "envs"
    if envs.is_dir():
        roots += [("env", p) for p in sorted(envs.iterdir()) if p.is_dir()]
    cache = pathlib.Path.home() / ".cache" / "rattler" / "cache" / "pkgs"
    if cache.is_dir():
        roots += [
            ("cache", p)
            for p in sorted(cache.iterdir())
            if p.is_dir() and p.name.startswith("playwright-")
        ]
    return roots


def _check_one(kind: str, root: pathlib.Path) -> list[dict]:
    findings: list[dict] = []
    cli = root / CLI_REL
    if cli.is_file():
        try:
            head = cli.read_text(errors="replace")[:400]
        except OSError as exc:  # unreadable is a real signal, not a pass
            findings.append(
                {"code": "cli-unreadable", "path": str(cli), "detail": str(exc)}
            )
            head = ""
        if head and not head.startswith(NODE_SHEBANG):
            findings.append(
                {
                    "code": "cli-clobbered",
                    "path": str(cli),
                    "detail": "cli.js is not the Node shim; the Python console "
                    "script was written through bin/playwright's symlink",
                }
            )
            # A dangling interpreter dates the damage: the env that caused it
            # is gone, so this has been broken for a while.
            for line in head.splitlines()[:3]:
                if "exec'" in line:
                    parts = [p for p in line.split('"') if p.startswith("/")]
                    if parts and not pathlib.Path(parts[0]).exists():
                        findings.append(
                            {
                                "code": "cli-dangling-interp",
                                "path": str(cli),
                                "detail": f"names a missing interpreter: {parts[0]}",
                            }
                        )
    if kind != "env":
        return findings

    # bin/ checks only make sense for a real environment.
    meta = root / "conda-meta"
    has_py = meta.is_dir() and any(meta.glob("playwright-python-*.json"))
    if has_py:
        binp = root / "bin" / "playwright"
        if binp.is_symlink():
            findings.append(
                {
                    "code": "bin-is-symlink",
                    "path": str(binp),
                    "detail": "bin/playwright is a symlink into node_modules; a "
                    "write here corrupts cli.js instead of replacing a file",
                }
            )
        elif not binp.exists():
            findings.append(
                {
                    "code": "bin-missing",
                    "path": str(binp),
                    "detail": "playwright-python is installed but its console "
                    "script is absent (its content likely went into cli.js)",
                }
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    try:
        repo = _repo_root()
        roots = _candidate_roots(repo)
    except OSError as exc:
        print(f"playwright-cli-integrity-check: could not run: {exc}", file=sys.stderr)
        return 2

    findings: list[dict] = []
    checked = 0
    for kind, root in roots:
        if not (root / CLI_REL).is_file() and kind == "cache":
            continue
        checked += 1
        findings += _check_one(kind, root)

    if args.json:
        print(json.dumps({"checked": checked, "findings": findings}, indent=2))
    elif findings:
        print(f"playwright-cli-integrity-check: {len(findings)} finding(s)")
        for f in findings:
            print(f"  [{f['code']}] {f['path']}\n      {f['detail']}")
        print(
            "\nRepair: restore cli.js by TRUNCATING IN PLACE "
            "(`cat <pristine> > cli.js`) so every hardlinked copy is fixed at "
            "once, and recreate bin/playwright as a regular file. See this "
            "script's docstring."
        )
    else:
        print(
            f"playwright-cli-integrity-check: clean "
            f"({checked} prefix(es) checked, no clobbered CLI)"
        )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
