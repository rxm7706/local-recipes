"""Meta test — the ``extract/`` no-execution zone AST denylist (Story 1.2).

NFR-S1: the extractor parses untrusted input as DATA, never executes it.
This guard AST-scans every module under the installed package's ``extract/``
and fails on:

* any import of ``subprocess``, ``jinja2``, ``pty``, ``ctypes``,
  ``multiprocessing``, ``pickle``, ``marshal``, ``shelve``, or ``runpy``
  (any form) — the deserialization modules execute code on parse, the
  canonical NFR-S1 violation for a module that reads untrusted files;
* ``from os import <member>`` for any forbidden os member (``system``,
  ``popen``, the full ``exec*``/``spawn*`` families, ``posix_spawn``/
  ``posix_spawnp``, ``fork``/``forkpty``, ``startfile``) and
  ``from builtins import eval/exec/compile/__import__``;
* calls to ``eval``/``exec``/``compile``/``__import__`` — as bare names OR
  as attributes through any name bound to the ``builtins`` module
  (``import builtins; builtins.eval(...)``);
* calls to any forbidden os member through any name bound to the os
  module, or unsafe ``yaml.load`` (through any name bound to the yaml
  module; ``yaml.safe_load`` is legal);
* subprocess-without-``subprocess``: ``asyncio.create_subprocess_exec``/
  ``create_subprocess_shell`` (bare, from-imported, through any name
  bound to asyncio — chained ``asyncio.subprocess.create_subprocess_exec``
  included) plus the ``asyncio.subprocess`` submodule import itself
  (``import asyncio.subprocess`` and ``from asyncio import subprocess``,
  aliased or not) and ``ProcessPoolExecutor`` (bare, from-imported, or
  as an attribute through ANY base — ``concurrent.futures.
  ProcessPoolExecutor(...)`` included);
* star imports of any sensitive module (``from os import *`` binds
  ``system`` as a bare name the call-site checks cannot see — denied
  wholesale for os/builtins/asyncio, every forbidden module, and every
  network module);
* any import of a NETWORK module (``socket``, ``ssl``, ``http``,
  ``urllib`` — ``urllib.parse`` included, deliberately overbroad —
  ``ftplib``/``smtplib``/``poplib``/``imaplib``/``telnetlib``/``xmlrpc``
  and the third-party ``requests``/``httpx``/``urllib3``/``aiohttp``):
  NFR-S2's no-egress claim for the parse zone was previously enforced
  only by the TEST-scope socket-deny harness; this is the static
  production-side backstop (the extract zone parses DATA — it has no
  legitimate network use).

Positively asserts the extract package exists and was scanned, and that the
detectors fire on synthetic violations — the guard is alive, not vacuous.

Bounds (stated, not aspirational): a best-effort STATIC check, like the 1.1
sole-ownership guard — ``getattr`` indirection, ``importlib`` dynamic
imports, string-built attribute access, and plain-assignment module
aliasing (``x = os; x.system(...)``) are out of scope; the socket-deny
harness and the conformance suite are the behavioral backstop.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import python_deptry_osv_scanner

_PACKAGE_FILE = python_deptry_osv_scanner.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
EXTRACT_DIR = Path(_PACKAGE_FILE).resolve().parent / "extract"

FORBIDDEN_MODULES = frozenset(
    {
        "subprocess",
        "jinja2",
        "pty",
        "ctypes",
        "multiprocessing",
        # deserialization that executes code on parse — the canonical
        # NFR-S1 violation for a module reading untrusted files
        "pickle",
        "marshal",
        "shelve",
        # executes Python source/modules by path
        "runpy",
    }
)
FORBIDDEN_OS_MEMBERS = frozenset(
    {
        "system",
        "popen",
        # the exec* family (process-image replacement)
        "execl",
        "execle",
        "execlp",
        "execlpe",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        # the spawn* family
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        # posix_spawn proper
        "posix_spawn",
        "posix_spawnp",
        # process creation without a command string
        "fork",
        "forkpty",
        # Windows: executes the file's associated application
        "startfile",
    }
)
FORBIDDEN_BUILTIN_CALLS = frozenset({"eval", "exec", "compile", "__import__"})
# Subprocess-without-``subprocess``: asyncio's subprocess API and the
# process-pool executor spawn processes without any denylisted import.
FORBIDDEN_ASYNCIO_MEMBERS = frozenset(
    {"create_subprocess_exec", "create_subprocess_shell"}
)
FORBIDDEN_BARE_CALLS = FORBIDDEN_ASYNCIO_MEMBERS | {"ProcessPoolExecutor"}
# NFR-S2 static backstop: the parse zone has NO legitimate network use.
# Top-level match, so ``urllib.parse`` is denied with the rest of urllib —
# deliberately overbroad (carve out only with a recorded decision).
FORBIDDEN_NETWORK_MODULES = frozenset(
    {
        "socket",
        "ssl",
        "http",
        "urllib",
        "ftplib",
        "smtplib",
        "poplib",
        "imaplib",
        "telnetlib",
        "xmlrpc",
        # third-party clients (should also fail at import, but the guard
        # must not depend on the env lacking them)
        "requests",
        "httpx",
        "urllib3",
        "aiohttp",
    }
)
# Modules whose star import would bind forbidden members as bare names the
# call-site checks cannot see.
STAR_IMPORT_DENIED = (
    FORBIDDEN_MODULES | FORBIDDEN_NETWORK_MODULES | {"os", "builtins", "asyncio"}
)


def _extract_modules() -> list[Path]:
    return sorted(EXTRACT_DIR.rglob("*.py"))


def _module_aliases(tree: ast.Module, module: str) -> frozenset[str]:
    """Names bound to ``module`` itself (``import os as o`` etc.)."""
    names = {module}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            if alias.name.split(".")[0] == module:
                names.add(alias.asname or alias.name.split(".")[0])
    return frozenset(names)


def _attr_root(func: ast.Attribute) -> str | None:
    """The base ``Name`` of a (possibly chained) attribute access —
    ``asyncio.subprocess.create_subprocess_exec`` roots at ``asyncio``."""
    node: ast.expr = func.value
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _violations(tree: ast.Module) -> list[str]:
    found: list[str] = []
    os_names = _module_aliases(tree, "os")
    yaml_names = _module_aliases(tree, "yaml")
    builtins_names = _module_aliases(tree, "builtins")
    asyncio_names = _module_aliases(tree, "asyncio")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in (
                    FORBIDDEN_MODULES | FORBIDDEN_NETWORK_MODULES
                ):
                    found.append(f"import {alias.name} (line {node.lineno})")
                elif alias.name == "asyncio.subprocess" or alias.name.startswith(
                    "asyncio.subprocess."
                ):
                    # The canonical stdlib spelling of the asyncio
                    # subprocess API: the submodule import itself is the
                    # capability.
                    found.append(f"import {alias.name} (line {node.lineno})")
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            if (
                any(alias.name == "*" for alias in node.names)
                and top in STAR_IMPORT_DENIED
            ):
                # A star import binds forbidden members as bare names the
                # call-site checks cannot see: denied wholesale.
                found.append(
                    f"from {node.module} import * (line {node.lineno})"
                )
            if top in FORBIDDEN_MODULES | FORBIDDEN_NETWORK_MODULES:
                found.append(
                    f"from {node.module} import ... (line {node.lineno})"
                )
            elif top == "os":
                found.extend(
                    f"from os import {alias.name} (line {node.lineno})"
                    for alias in node.names
                    if alias.name in FORBIDDEN_OS_MEMBERS
                )
            elif top == "builtins":
                found.extend(
                    f"from builtins import {alias.name} (line {node.lineno})"
                    for alias in node.names
                    if alias.name in FORBIDDEN_BUILTIN_CALLS
                )
            elif top == "yaml":
                found.extend(
                    f"from yaml import load (line {node.lineno})"
                    for alias in node.names
                    if alias.name == "load"
                )
            elif top == "asyncio":
                found.extend(
                    f"from asyncio import {alias.name} (line {node.lineno})"
                    for alias in node.names
                    # ``from asyncio import subprocess [as x]`` imports the
                    # submodule — the capability itself, whatever it's
                    # bound to (it even shadows the name ``subprocess``
                    # without tripping the module denylist).
                    if alias.name in FORBIDDEN_ASYNCIO_MEMBERS | {"subprocess"}
                )
            elif top == "concurrent":
                found.extend(
                    f"from {node.module} import {alias.name} "
                    f"(line {node.lineno})"
                    for alias in node.names
                    if alias.name == "ProcessPoolExecutor"
                )
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in (
                FORBIDDEN_BUILTIN_CALLS | FORBIDDEN_BARE_CALLS
            ):
                found.append(f"{func.id}() call (line {node.lineno})")
            elif isinstance(func, ast.Attribute):
                # ProcessPoolExecutor fires through ANY base, chained
                # attribute access included (concurrent.futures.
                # ProcessPoolExecutor(...)).
                if func.attr == "ProcessPoolExecutor":
                    found.append(
                        f"ProcessPoolExecutor() call (line {node.lineno})"
                    )
                elif (
                    func.attr in FORBIDDEN_ASYNCIO_MEMBERS
                    and _attr_root(func) in asyncio_names
                ):
                    # Chain-rooted: covers both asyncio.create_subprocess_*
                    # and the canonical asyncio.subprocess.create_subprocess_*
                    # spelling (any alias of asyncio as the root).
                    found.append(
                        f"asyncio.{func.attr}() call (line {node.lineno})"
                    )
                elif isinstance(func.value, ast.Name):
                    base = func.value.id
                    if base in os_names and func.attr in FORBIDDEN_OS_MEMBERS:
                        found.append(
                            f"os.{func.attr}() call (line {node.lineno})"
                        )
                    elif (
                        base in builtins_names
                        and func.attr in FORBIDDEN_BUILTIN_CALLS
                    ):
                        found.append(
                            f"builtins.{func.attr}() call (line {node.lineno})"
                        )
                    elif base in yaml_names and func.attr == "load":
                        found.append(f"yaml.load() call (line {node.lineno})")
    return found


def test_extract_zone_exists_and_is_scanned():
    """Non-vacuous proof: the zone exists and the guard has a surface."""
    assert EXTRACT_DIR.is_dir(), "extract/ missing from the installed package"
    modules = _extract_modules()
    assert len(modules) >= 2, (  # __init__.py + pyproject.py at minimum
        f"extract/ scan surface unexpectedly small: {modules}"
    )


@pytest.mark.parametrize("module_path", _extract_modules(), ids=lambda p: p.name)
def test_extract_module_has_no_execution_primitives(module_path: Path):
    tree = ast.parse(module_path.read_text(encoding="utf-8"), str(module_path))
    violations = _violations(tree)
    assert not violations, (
        f"{module_path.name} violates the no-execution zone (NFR-S1): "
        f"{violations}"
    )


def test_detector_fires_on_forbidden_imports():
    assert _violations(ast.parse("import subprocess\n"))
    assert _violations(ast.parse("import subprocess.run\n"))
    assert _violations(ast.parse("from subprocess import run\n"))
    assert _violations(ast.parse("import jinja2\n"))
    assert _violations(ast.parse("from jinja2 import Template\n"))
    assert _violations(ast.parse("from os import system\n"))
    assert _violations(ast.parse("from os import popen\n"))
    assert _violations(ast.parse("from builtins import eval\n"))
    assert not _violations(ast.parse("import tomllib\nimport os\n"))


def test_detector_fires_on_forbidden_calls():
    assert _violations(ast.parse("eval('x')\n"))
    assert _violations(ast.parse("exec('x')\n"))
    assert _violations(ast.parse("import os\nos.system('ls')\n"))
    assert _violations(ast.parse("import os as o\no.popen('ls')\n"))
    assert _violations(ast.parse("import yaml\nyaml.load(stream)\n"))
    assert _violations(ast.parse("import yaml as y\ny.load(stream)\n"))
    assert not _violations(ast.parse("import yaml\nyaml.safe_load(stream)\n"))
    assert not _violations(ast.parse("value = evaluate('x')\n"))


def test_detector_fires_on_compile_and_dunder_import():
    """compile() and __import__() are execution primitives too — the guard
    is alive on both, bare or via builtins."""
    assert _violations(ast.parse("compile('x', '<s>', 'eval')\n"))
    assert _violations(ast.parse("__import__('os')\n"))
    assert _violations(ast.parse("from builtins import compile\n"))
    assert _violations(ast.parse("from builtins import __import__\n"))
    assert not _violations(ast.parse("value = recompile('x')\n"))


def test_detector_fires_on_builtins_bound_attribute_calls():
    """``import builtins; builtins.eval(...)`` must not slip past the
    bare-name check — attribute calls through any name bound to the
    builtins module fire."""
    assert _violations(ast.parse("import builtins\nbuiltins.eval('x')\n"))
    assert _violations(ast.parse("import builtins as b\nb.exec('x')\n"))
    assert _violations(
        ast.parse("import builtins\nbuiltins.compile('x', '<s>', 'exec')\n")
    )
    assert _violations(ast.parse("import builtins\nbuiltins.__import__('os')\n"))
    assert not _violations(ast.parse("import builtins\nbuiltins.len([])\n"))


@pytest.mark.parametrize("member", sorted(FORBIDDEN_OS_MEMBERS))
def test_detector_fires_on_each_forbidden_os_member(member: str):
    """Guard-alive proof per os member: attribute call, aliased-module
    attribute call, AND the from-import form all fire."""
    assert _violations(ast.parse(f"import os\nos.{member}(x)\n"))
    assert _violations(ast.parse(f"import os as o\no.{member}(x)\n"))
    assert _violations(ast.parse(f"from os import {member}\n"))


def test_detector_ignores_benign_os_usage():
    assert not _violations(ast.parse("import os\nos.getcwd()\n"))
    assert not _violations(ast.parse("from os import path\n"))


def test_detector_fires_on_new_forbidden_imports():
    """pty, ctypes, and multiprocessing join subprocess/jinja2 on the
    forbidden-import list (every import form)."""
    assert _violations(ast.parse("import pty\n"))
    assert _violations(ast.parse("from pty import spawn\n"))
    assert _violations(ast.parse("import ctypes\n"))
    assert _violations(ast.parse("import ctypes.util\n"))
    assert _violations(ast.parse("from ctypes import CDLL\n"))
    assert _violations(ast.parse("import multiprocessing\n"))
    assert _violations(ast.parse("from multiprocessing import Process\n"))
    assert _violations(ast.parse("import multiprocessing.pool\n"))
    assert not _violations(ast.parse("import tomllib\nimport math\n"))


def test_detector_fires_on_deserialization_and_runpy_imports():
    """pickle/marshal/shelve execute code on parse; runpy executes modules
    by path — every import form fires."""
    assert _violations(ast.parse("import pickle\n"))
    assert _violations(ast.parse("from pickle import loads\n"))
    assert _violations(ast.parse("import marshal\n"))
    assert _violations(ast.parse("from marshal import loads\n"))
    assert _violations(ast.parse("import shelve\n"))
    assert _violations(ast.parse("import runpy\n"))
    assert _violations(ast.parse("from runpy import run_path\n"))
    assert not _violations(ast.parse("import json\n"))


def test_detector_fires_on_fork_and_startfile():
    assert _violations(ast.parse("import os\nos.fork()\n"))
    assert _violations(ast.parse("from os import fork\n"))
    assert _violations(ast.parse("import os\nos.forkpty()\n"))
    assert _violations(ast.parse("import os\nos.startfile(path)\n"))
    assert _violations(ast.parse("from os import startfile\n"))


def test_detector_fires_on_subprocess_without_subprocess():
    """asyncio's subprocess API and ProcessPoolExecutor spawn processes
    without any denylisted import — bare, from-imported, aliased, and
    chained-attribute forms all fire."""
    assert _violations(
        ast.parse("import asyncio\nasyncio.create_subprocess_exec(x)\n")
    )
    assert _violations(
        ast.parse("import asyncio as aio\naio.create_subprocess_shell(x)\n")
    )
    assert _violations(
        ast.parse("from asyncio import create_subprocess_exec\n")
    )
    assert _violations(ast.parse("create_subprocess_exec(x)\n"))
    assert _violations(
        ast.parse("from concurrent.futures import ProcessPoolExecutor\n")
    )
    assert _violations(ast.parse("ProcessPoolExecutor()\n"))
    assert _violations(
        ast.parse(
            "import concurrent.futures\n"
            "concurrent.futures.ProcessPoolExecutor()\n"
        )
    )
    assert not _violations(
        ast.parse("from concurrent.futures import ThreadPoolExecutor\n")
    )
    assert not _violations(ast.parse("import asyncio\nasyncio.run(main())\n"))


def test_detector_fires_on_asyncio_subprocess_submodule_forms():
    """The canonical stdlib spellings of the asyncio subprocess API — the
    submodule import itself and the chained-attribute call — must fire
    (previously only the top-level asyncio attribute forms did)."""
    assert _violations(ast.parse("import asyncio.subprocess\n"))
    assert _violations(
        ast.parse(
            "import asyncio\nasyncio.subprocess.create_subprocess_exec(x)\n"
        )
    )
    assert _violations(
        ast.parse(
            "import asyncio.subprocess\n"
            "asyncio.subprocess.create_subprocess_exec(x)\n"
        )
    )
    assert _violations(ast.parse("from asyncio import subprocess\n"))
    assert _violations(ast.parse("from asyncio import subprocess as asp\n"))
    assert _violations(
        ast.parse(
            "import asyncio as aio\n"
            "aio.subprocess.create_subprocess_shell(x)\n"
        )
    )
    assert not _violations(
        ast.parse("import asyncio\nasyncio.get_event_loop()\n")
    )


def test_detector_fires_on_star_imports_of_sensitive_modules():
    """``from os import *`` binds ``system`` as a bare name the call-site
    checks cannot see: star imports of sensitive modules are denied
    wholesale."""
    assert _violations(ast.parse("from os import *\nsystem('ls')\n"))
    assert _violations(ast.parse("from os import *\n"))
    assert _violations(ast.parse("from asyncio import *\n"))
    assert _violations(ast.parse("from builtins import *\n"))
    assert _violations(ast.parse("from subprocess import *\n"))
    assert _violations(ast.parse("from socket import *\n"))
    assert not _violations(ast.parse("from pathlib import *\n"))


def test_detector_fires_on_network_module_imports():
    """NFR-S2 static backstop: the parse zone has no legitimate network
    use — every import form of a network module fires (the socket-deny
    harness only covers TEST-time behavior; this covers the production
    source)."""
    assert _violations(ast.parse("import socket\n"))
    assert _violations(ast.parse("import socket as s\n"))
    assert _violations(ast.parse("from socket import create_connection\n"))
    assert _violations(ast.parse("import ssl\n"))
    assert _violations(ast.parse("import urllib.request\n"))
    assert _violations(ast.parse("from urllib.request import urlopen\n"))
    assert _violations(ast.parse("import http.client\n"))
    assert _violations(ast.parse("from http.client import HTTPConnection\n"))
    assert _violations(ast.parse("import ftplib\n"))
    assert _violations(ast.parse("import smtplib\n"))
    assert _violations(ast.parse("import xmlrpc.client\n"))
    assert _violations(ast.parse("import requests\n"))
    assert _violations(ast.parse("import httpx\n"))
    assert _violations(ast.parse("import urllib3\n"))
    assert _violations(ast.parse("import aiohttp\n"))
    # urllib.parse is deliberately overbroad-denied (top-level match).
    assert _violations(ast.parse("from urllib.parse import quote\n"))
    assert not _violations(ast.parse("import json\nimport tomllib\n"))
    assert not _violations(ast.parse("from packaging.requirements import Requirement\n"))
