"""Steward's `keys` duty-adapter module (AD-1/AD-2) — Epic 1's single file.

Story 1.2 slice: a host-scoped credential resolver (FR-7) and a drift-detection
primitive (FR-4) that AST-scans a Python source file for the historical
unconditional-injection shape `_http.py` had before commit ``a4137cdfa3``.
Both pieces delegate entirely to `.claude/skills/conda-forge-expert/scripts/
_http.py`'s ``auth_headers_for`` — this module decides only *host membership*
and *whether a function's header-attachment is gated*; it never builds its own
request/header logic (AD-1, AD-2: delegate, never reimplement).

Story 1.3 slice: `encrypt_file`/`decrypt_file`, thin subprocess wraps of the
real `age` CLI (AD-1/AD-3 — never vendored/reimplemented crypto), and a
second, distinct scan primitive — `PlaintextSecretFinding`, a small fixed
pattern table, `scan_file_for_secrets`/`scan_directory_for_secrets` — that
flags committed content plausibly matching a known secret shape. `KeysDuty`
is the `Duty`-conforming adapter `cli.py`'s `resolve_duty("keys")` now
returns, wiring `steward keys encrypt`/`steward keys decrypt`. There is still
no `steward keys audit` verb — Story 1.6 exposes both this module's findings
(`DriftFinding` and `PlaintextSecretFinding`) through one CLI verb.

Story 1.4 slice: `.steward/keys-inventory.yaml` (FR-5) — `KeyIdentityEntry`,
`InventoryError`, `load_inventory`/`save_inventory` (`yaml.safe_load`/
`safe_dump` only) — plus `generate_identity` (an `age-keygen` subprocess
wrap) and `rotate_identity`, which re-encrypts every secret an `issued`/
`active` scope owns onto a freshly generated identity and retires the old
one. Wired as `steward keys rotate --scope --new-identity [--inventory]`.
No calendar/cron/scheduler path exists anywhere in this module — rotation
is on-demand only (FR-3), pinned by `tests/meta/test_invariants.py`'s
`test_no_rotation_scheduler_exists`.

Story 1.5 slice: `format_inventory` — read-only text/`--json` rendering of
the inventory (`steward keys list`), built strictly from `KeyIdentityEntry`
fields; never opens `identity_path` or a `secrets` path, so a raw secret
value structurally cannot appear in either format (NFR-7).

Stories 1.6-1.7 continue to extend this same file (the architecture's
single duty-adapter-module design for Epic 1) rather than splitting it into
a subpackage.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import stat
import subprocess
import sys
import tempfile
import tokenize
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml

from .interfaces import DutyResult

# ── Bridge to the real, already-fixed `_http.py` (AD-2: delegate, never reimplement) ──

_HTTP_MODULE_MARKER = Path(".claude/skills/conda-forge-expert/scripts/_http.py")


def locate_http_module() -> Path:
    """Return the path to `.claude/skills/conda-forge-expert/scripts/_http.py`.

    Walks up from this file's own resolved location looking for the marker
    path, rather than hardcoding a fixed number of ``.parent`` hops — robust
    to whatever depth the installed/editable `pyforge-steward` package ends
    up at relative to the repo root.
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        candidate = ancestor / _HTTP_MODULE_MARKER
        if candidate.is_file():
            return candidate
    raise RuntimeError(
        f"keys.py: could not locate {_HTTP_MODULE_MARKER} by walking up from "
        f"{here} — this module must live inside a local-recipes checkout."
    )


_HTTP_SCRIPTS_DIR = str(locate_http_module().parent)
if _HTTP_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _HTTP_SCRIPTS_DIR)

from _http import auth_headers_for  # noqa: E402  # the delegate target (AD-1/AD-2)


# ── Host-scoped credential resolver (FR-7) ──────────────────────────────────

@dataclass(frozen=True)
class HostScopedCredential:
    """A credential explicitly scoped to a declared host allowlist.

    ``hosts`` is the ONLY gate `resolve_headers` honors — a URL whose host is
    not in this tuple never sees this credential's headers, even if the
    backing env var (e.g. ``JFROG_API_KEY``) is set. This is the reusable
    primitive `_http.py`'s per-call-site ``skip_auth`` opt-out did not provide:
    that parameter must be remembered at every call site, while this credential
    declares its allowlist once.

    Scope note: this gate decides *whether* ambient auth may attach to a URL
    at all. When the host is in-allowlist, `_http.py`'s auth chain still
    decides *which* ambient credential attaches (its JFrog env vars take
    priority for any host) — this primitive does not select headers per
    credential. Per-credential selection is a later-story concern (the
    dataclass does not yet carry the credential's identity).

    Matching is by exact canonical hostname — ports, brackets, and trailing
    root dots are normalized away, and subdomains of an entry do NOT match.
    """

    hosts: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.hosts, str) or not isinstance(self.hosts, tuple):
            raise TypeError(
                f"HostScopedCredential.hosts must be a tuple of hostnames, "
                f"got {type(self.hosts).__name__!r} — a bare string iterates "
                "per-character and silently never matches any real host"
            )
        if not self.hosts:
            raise ValueError(
                "HostScopedCredential.hosts must not be empty — an empty "
                "allowlist can never match any URL, silently disabling the "
                "credential"
            )
        if not all(isinstance(h, str) for h in self.hosts):
            raise TypeError("HostScopedCredential.hosts entries must all be strings")
        for h in self.hosts:
            if "/" in h:
                raise ValueError(
                    f"HostScopedCredential.hosts entry {h!r} looks like a URL "
                    "— entries must be bare hostnames (no scheme or path), or "
                    "the credential silently never matches"
                )
            if any(c.isspace() for c in h) or set(h) & set("@?#*"):
                raise ValueError(
                    f"HostScopedCredential.hosts entry {h!r} contains "
                    "characters that can never appear in a parsed URL "
                    "hostname — the credential would silently never match"
                )
            if not h.startswith("[") and h.count(":") == 1:
                port = h.rsplit(":", 1)[1]
                if not port.isdigit():
                    raise ValueError(
                        f"HostScopedCredential.hosts entry {h!r} looks "
                        f"port-qualified but {port!r} is not a numeric port "
                        "— a mistyped entry (e.g. 'https:host') would "
                        "otherwise silently never match, or match a "
                        "hostname the author never wrote"
                    )
            if not _canonical_host(h):
                raise ValueError(
                    f"HostScopedCredential.hosts entry {h!r} canonicalizes to "
                    "an empty hostname — it could never match a real host, "
                    "and would match hostname-less strings passed as URLs"
                )


def _canonical_host(host: str) -> str:
    """Lowercase, drop any port suffix, IPv6 brackets, and trailing root dot.

    Matches ``urlparse(url).hostname``'s own canonicalization (lowercase,
    unbracketed, no port) so a declared allowlist entry and the URL being
    checked compare on the same basis — without this, a `hosts` entry written
    with a port (e.g. ``"artifactory.example.com:8081"``) or a trailing-dot
    FQDN would never match and silently disable the credential. An IPv6
    literal keeps all its colon groups: only a bracketed suffix
    (``"[::1]:8081"``) or a single-colon ``host:port`` is treated as
    port-qualified — a bare multi-colon host is an address, and blindly
    ``rsplit``-ing it would collapse distinct IPv6 hosts into one. A
    single-colon suffix is stripped only when it is all digits (a real
    port): treating an arbitrary suffix as a port would mis-canonicalize a
    mistyped entry like ``"https:host"`` into ``"https"`` — a hostname the
    author never wrote (`__post_init__` rejects such entries loudly).
    """
    host = host.strip().lower()
    if host.startswith("["):
        end = host.find("]")
        host = host[1:end] if end != -1 else host[1:]
    elif host.count(":") == 1:
        base, _, port = host.rpartition(":")
        if port.isdigit():
            host = base
    return host.rstrip(".")


def resolve_headers(credential: HostScopedCredential, url: str) -> dict[str, str]:
    """Return the auth headers `_http.py` would produce for `url`, host-gated.

    Computes only whether `url`'s host is inside `credential.hosts`, then
    passes that decision straight through as `_http.py`'s existing
    ``skip_auth`` parameter (AD-2) — the header-building itself stays entirely
    inside `auth_headers_for`. Outside the allowlist: ``{}``, unconditionally,
    even when the matching env var is set. Inside the allowlist: whatever
    `auth_headers_for` resolves for that host (including ``{}`` if no
    credential env var is set).

    A `url` with no parseable hostname (e.g. a scheme-less string, which
    ``urlparse`` reads as all-path) fails closed to ``{}``; a malformed
    bracketed-IPv6 `url` raises ``ValueError`` from ``urlparse`` —
    propagated, not swallowed.
    """
    host = _canonical_host(urlparse(url).hostname or "")
    in_allowlist = host in {_canonical_host(h) for h in credential.hosts}
    return auth_headers_for(url, skip_auth=not in_allowlist)


# ── Drift-detection primitive (FR-4) ────────────────────────────────────────
#
# Targets exactly one defect shape — not a pluggable static-analysis
# framework. See "Design Notes" in this story's spec for the full heuristic;
# summarized here where the code implements it.

@dataclass(frozen=True)
class DriftFinding:
    """One occurrence of the pre-fix unconditional-injection shape."""

    function: str
    line: int
    message: str


def scan_source(source: str) -> list[DriftFinding]:
    """Scan Python `source` for the pre-fix unconditional-injection shape.

    For every function, walks its top-level statements in order looking for
    an ``os.environ``-sourced value assigned into a subscripted target (e.g.
    ``headers["X"] = os.environ["Y"]`` — not necessarily a variable literally
    named ``headers``) that is not preceded by a **scope gate** — a top-level
    ``if <cond>: return ...`` whose `<cond>` is not itself just a presence
    check of the same env var being read (e.g. ``if
    os.environ.get("JFROG_API_KEY"):`` guarding its own attachment is NOT a
    scope gate: it narrows on whether the secret exists, never on which host
    it may attach to). ``if skip_auth: return {}`` IS a scope gate, and once
    one is seen, no later statement in that function is flagged.

    This targets exactly the `_http.py` unconditional-injection shape, not
    general env-to-dict flows — it is deliberately not a general-purpose
    static-analysis framework (see this story's spec, "Never"), so it can
    still flag env-sourced dict assignments that have nothing to do with
    credentials if pointed at unrelated source.

    Raises ``SyntaxError`` on malformed `source` — propagated, not swallowed.
    """
    tree = ast.parse(source)
    findings: list[DriftFinding] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            findings.extend(_scan_function(node))
    return findings


def scan_file(path: str | Path) -> list[DriftFinding]:
    """`scan_source` over the contents of the file at `path`.

    Opened with ``tokenize.open`` so a PEP 263 encoding cookie is honored —
    a non-UTF-8 source file is scanned rather than raising
    ``UnicodeDecodeError``.
    """
    with tokenize.open(path) as f:
        return scan_source(f.read())


def _scan_function(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[DriftFinding]:
    findings: list[DriftFinding] = []
    for stmt in func.body:
        if _is_scope_gate(stmt):
            break
        findings.extend(_find_credential_assignments(stmt, func.name))
    return findings


def _is_scope_gate(stmt: ast.stmt) -> bool:
    """A top-level ``if <cond>: return ...`` that is not an env-presence check.

    This is exactly what ``if skip_auth: return {}`` provides in the fixed
    `auth_headers_for`: everything after it is unreachable unless the gate
    condition is false, so nothing later in the function can be an
    *unconditional* attachment.
    """
    if not isinstance(stmt, ast.If):
        return False
    if _is_env_presence_check(stmt.test):
        return False
    return any(isinstance(inner, ast.Return) for inner in stmt.body)


def _is_env_presence_check(test: ast.expr) -> bool:
    """True if `test` is exactly ``os.environ.get(...)`` or ``os.environ[...]``."""
    if isinstance(test, ast.Call):
        func = test.func
        return (
            isinstance(func, ast.Attribute)
            and func.attr == "get"
            and _is_os_environ_expr(func.value)
        )
    if isinstance(test, ast.Subscript):
        return _is_os_environ_expr(test.value)
    return False


def _is_os_environ_expr(node: ast.expr) -> bool:
    """True if `node` is the expression ``os.environ``."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _reads_os_environ(node: ast.AST) -> bool:
    """True if ``os.environ[...]`` or ``os.environ.get(...)`` appears anywhere in `node`."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Subscript) and _is_os_environ_expr(sub.value):
            return True
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr == "get"
            and _is_os_environ_expr(sub.func.value)
        ):
            return True
    return False


def _find_credential_assignments(stmt: ast.stmt, func_name: str) -> list[DriftFinding]:
    """Recurse into `stmt` for header-dict assignments sourced from `os.environ`.

    Descends into ``if`` bodies (both branches) so a credential attachment
    nested inside a presence check (``if os.environ.get("X"): headers["Y"] =
    os.environ["X"]``) is still found — a presence check narrows on *whether
    the secret exists*, never on *which host it may attach to*, so it
    provides no host protection and the assignment beneath it is still
    unconditional with respect to the URL.
    """
    findings: list[DriftFinding] = []
    if isinstance(stmt, ast.Assign):
        for target in stmt.targets:
            if isinstance(target, ast.Subscript) and _reads_os_environ(stmt.value):
                findings.append(
                    DriftFinding(
                        function=func_name,
                        line=stmt.lineno,
                        message=(
                            f"{func_name}:{stmt.lineno} attaches a credential "
                            "header sourced from os.environ with no preceding "
                            "host-scope gate"
                        ),
                    )
                )
    elif isinstance(stmt, ast.If):
        for inner in (*stmt.body, *stmt.orelse):
            findings.extend(_find_credential_assignments(inner, func_name))
    return findings


# ── `age` subprocess primitives (FR-2) ──────────────────────────────────────
#
# Thin subprocess wraps of the real `age` CLI — no vendored/reimplemented
# crypto (AD-1, AD-3). Argument names mirror `age`'s own flags rather than
# inventing Steward-specific ones (see this story's spec, "Design Notes").
# `subprocess.CalledProcessError` is left to propagate here — caught only at
# the `KeysDuty` boundary — matching `scan_source`'s `SyntaxError` precedent
# of not swallowing errors at the primitive level.

def _reject_dash(role: str, value: str | Path) -> None:
    """Refuse `age`'s `-` stdin/stdout sentinel for a single named `role`.

    `-` survives the `--` separator (it is a positional value `age`/
    `age-keygen` special-case, not a flag), but every subprocess wrap in this
    module closes stdin and discards captured stdout — so `-` as an input
    would read the empty DEVNULL stream and `-` as an output would report
    success while the real payload vanished into the discarded capture. Both
    are silent data loss; raise instead. Generalized out of the original
    two-role `encrypt_file`/`decrypt_file` check (Story 1.3) so `rotate`'s
    single `--new-identity` path (Story 1.4) reuses the exact same message
    shape without a role-less pairwise loop.
    """
    if str(value) == "-":
        raise ValueError(
            f"{role} path '-' means stdin/stdout to age, which this "
            "wrapper closes/discards — pass a real path (e.g. ./-)"
        )


def _reject_stdio_sentinel(input_path: str | Path, output: str | Path) -> None:
    """`_reject_dash` for both of `encrypt_file`/`decrypt_file`'s paths."""
    _reject_dash("input", input_path)
    _reject_dash("output", output)


def encrypt_file(input_path: str | Path, *, recipient: str, output: str | Path) -> None:
    """`age --encrypt` `input_path` to `output` for `recipient`.

    Raises `subprocess.CalledProcessError` on a non-zero `age` exit (e.g. a
    malformed recipient) — propagated, not swallowed — and `ValueError` for a
    `-` input/output path (see `_reject_stdio_sentinel`). The `--` separator
    keeps a flag-shaped filename (`-r`) from being parsed as an `age` flag,
    the closed stdin keeps `age`'s stdin fallback from hanging an unattended
    run, and the lenient capture decode keeps a non-UTF-8 byte on `age`'s
    stderr (e.g. an echoed filename) from crashing the error path itself.
    """
    _reject_stdio_sentinel(input_path, output)
    subprocess.run(
        ["age", "--encrypt", "--recipient", recipient, "--output", str(output), "--", str(input_path)],
        check=True,
        capture_output=True,
        text=True,
        errors="replace",
        stdin=subprocess.DEVNULL,
    )


def decrypt_file(input_path: str | Path, *, identity: str | Path, output: str | Path) -> None:
    """`age --decrypt` `input_path` to `output` using the identity at `identity`.

    Raises `subprocess.CalledProcessError` on a non-zero `age` exit — most
    notably an identity that does not match any recipient the file was
    encrypted to (`age: error: no identity matched any of the recipients`) —
    and `ValueError` for a `-` input/output path. `--`, the closed stdin, and
    the lenient capture decode: same rationale as `encrypt_file`.
    """
    _reject_stdio_sentinel(input_path, output)
    subprocess.run(
        ["age", "--decrypt", "--identity", str(identity), "--output", str(output), "--", str(input_path)],
        check=True,
        capture_output=True,
        text=True,
        errors="replace",
        stdin=subprocess.DEVNULL,
    )


# ── Plaintext-secret scan primitive ─────────────────────────────────────────
#
# A small, fixed, named pattern table — not a pluggable/extensible rule
# engine (see this story's spec, "Never"). Targets exactly three known
# secret shapes: an Anthropic API key, a plaintext `age` identity (the exact
# unencrypted shape `encrypt_file` above exists to protect against), and a
# PEM private-key header. This is `PlaintextSecretFinding`, deliberately a
# distinct type from `DriftFinding` above — a committed plaintext secret and
# an ungated credential-attachment code path are unrelated defect shapes, and
# a caller must never conflate them. Story 1.6 wires a CLI verb; this story
# only proves the primitive (mirrors how 1.2 framed its own drift scan).

@dataclass(frozen=True)
class PlaintextSecretFinding:
    """One line of file content plausibly matching a known secret shape."""

    path: Path
    line: int
    pattern_name: str
    message: str


_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("anthropic-api-key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("age-identity", re.compile(r"AGE-SECRET-KEY-1[A-Z0-9]{20,}")),
    ("pem-private-key-header", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
)


def scan_file_for_secrets(path: str | Path) -> list[PlaintextSecretFinding]:
    """Scan the file at `path` for content matching `_SECRET_PATTERNS`.

    Reads raw bytes and decodes leniently (``errors="replace"``) rather than
    `scan_file`'s ``tokenize.open`` above — this primitive scans arbitrary
    file content, not just Python source, so a binary `.age` ciphertext
    sitting in the same directory must not crash the scan with a decode
    error. NUL bytes are stripped before matching so a UTF-16-encoded secret
    (interleaved NULs — e.g. a PowerShell-redirected key file) cannot
    silently scan as clean; other non-UTF-8 encodings remain out of scope.
    Lines split on ``\\n`` only (not ``str.splitlines``, which also splits on
    form feed/NEL/LS/PS) so a finding's `line` matches `grep -n`/editor
    numbering.
    """
    path = Path(path)
    text = path.read_bytes().decode("utf-8", errors="replace").replace("\x00", "")
    findings: list[PlaintextSecretFinding] = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        for pattern_name, pattern in _SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(
                    PlaintextSecretFinding(
                        path=path,
                        line=lineno,
                        pattern_name=pattern_name,
                        message=(
                            f"{path}:{lineno} matches the {pattern_name!r} "
                            "plaintext-secret pattern"
                        ),
                    )
                )
    return findings


def scan_directory_for_secrets(directory: str | Path) -> list[PlaintextSecretFinding]:
    """`scan_file_for_secrets` over every regular file under `directory`.

    Recurses — a committed secret can land at any depth in a tree, not just
    the top level. A directory with no secret-shaped content returns ``[]``.

    Raises `NotADirectoryError` if `directory` doesn't exist or isn't a
    directory, and propagates any `OSError` from the walk, an entry `stat`,
    or a file read (e.g. an unreadable subtree, a dangling symlink) — an
    audit primitive must never let a typo'd path or a permission wall
    silently read as "clean" when it never actually scanned everything.
    `Path.walk` (not ``rglob``) because the glob machinery swallows
    per-directory `PermissionError`, and its symlink-traversal default
    changed across 3.12/3.13; `walk` propagates via ``on_error`` and (pinned
    explicitly) never descends into directory symlinks. File symlinks are
    still followed — the follow/no-follow policy is a Story 1.6 decision
    (see deferred-work) — but one whose target can't be stat'd raises
    instead of silently skipping.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"scan_directory_for_secrets: not a directory: {directory}")

    def _propagate(error: OSError) -> None:
        raise error

    findings: list[PlaintextSecretFinding] = []
    for dirpath, dirnames, filenames in directory.walk(on_error=_propagate, follow_symlinks=False):
        dirnames.sort()
        for name in sorted(filenames):
            path = dirpath / name
            # stat(), not is_file(): is_file() swallows OSError, so a dangling
            # symlink or one into an unreadable tree would silently scan as
            # "clean" — the exact failure mode this contract forbids. The
            # S_ISREG check still skips non-regular files (FIFOs, sockets) so
            # a blocking special file can't hang the scan.
            if stat.S_ISREG(path.stat().st_mode):
                findings.extend(scan_file_for_secrets(path))
    return findings


# ── Credential inventory + rotation (FR-3/FR-5) ─────────────────────────────
#
# `.steward/keys-inventory.yaml`, the tracked, repo-root config location
# (ARCHITECTURE-SPINE.md's Consistency Conventions table). Stores only
# identity NAME/SCOPE/PROVENANCE/STATUS/LAST_ROTATED and a filesystem
# pointer (`identity_path`) to the actual `age` identity file — never the
# identity's own secret-key CONTENT. `load_inventory`/`save_inventory` are
# `yaml.safe_load`/`yaml.safe_dump` only (never `yaml.load`/`unsafe_load`),
# mirroring `pyforge-warden`'s `waiver.py` precedent.

_INVENTORY_RELATIVE_PATH = Path(".steward/keys-inventory.yaml")


def repo_root() -> Path:
    """The local-recipes checkout root.

    Reuses `locate_http_module`'s own walk-up search: the module it finds
    lives at ``<repo_root>/.claude/skills/conda-forge-expert/scripts/
    _http.py``, four `.parent` hops down from that file — so the ancestor
    the walk already matched IS the repo root, recovered without a second
    filesystem walk.
    """
    return locate_http_module().parents[4]


def default_inventory_path() -> Path:
    """`.steward/keys-inventory.yaml` at the repo root."""
    return repo_root() / _INVENTORY_RELATIVE_PATH


@dataclass(frozen=True)
class KeyIdentityEntry:
    """One row of the credential inventory. Never carries a secret value —
    `identity_path` is a filesystem pointer, not key material."""

    name: str
    scope: str
    provenance: str          # "issued" | "observed"
    status: str               # "active" | "retired"
    last_rotated: str | None
    identity_path: str | None
    secrets: tuple[str, ...] = ()


class InventoryError(ValueError):
    """A malformed inventory file, or an operation the inventory can't
    satisfy (e.g. rotating a scope with no issued/active entry)."""


_VALID_PROVENANCE = ("issued", "observed")
_VALID_STATUS = ("active", "retired")


def load_inventory(path: str | Path) -> tuple[KeyIdentityEntry, ...]:
    """Load `.steward/keys-inventory.yaml`-shaped YAML from `path`.

    A missing file loads as ``()`` — mirrors `pyforge-warden`'s
    `load_waivers` precedent (no inventory yet is a normal, not an error,
    state). Raises `InventoryError` for a malformed document (not a mapping,
    a missing required field, or an unrecognized `provenance`/`status`
    value) — a corrupt inventory must never silently read as empty.
    """
    path = Path(path)
    if not path.is_file():
        return ()
    with path.open("r", encoding="utf-8") as f:
        document = yaml.safe_load(f) or {}
    if not isinstance(document, dict):
        raise InventoryError(
            f"{path}: top-level document must be a mapping, got "
            f"{type(document).__name__}"
        )
    entries: list[KeyIdentityEntry] = []
    for raw in document.get("identities") or []:
        if not isinstance(raw, dict):
            raise InventoryError(f"{path}: each identity entry must be a mapping")
        try:
            entry = KeyIdentityEntry(
                name=raw["name"],
                scope=raw["scope"],
                provenance=raw["provenance"],
                status=raw["status"],
                last_rotated=raw.get("last_rotated"),
                identity_path=raw.get("identity_path"),
                secrets=tuple(raw.get("secrets") or ()),
            )
        except KeyError as exc:
            raise InventoryError(f"{path}: identity entry missing required field {exc}") from exc
        if entry.provenance not in _VALID_PROVENANCE:
            raise InventoryError(
                f"{path}: identity {entry.name!r} has unknown provenance {entry.provenance!r}"
            )
        if entry.status not in _VALID_STATUS:
            raise InventoryError(
                f"{path}: identity {entry.name!r} has unknown status {entry.status!r}"
            )
        entries.append(entry)
    return tuple(entries)


def save_inventory(path: str | Path, entries: tuple[KeyIdentityEntry, ...]) -> None:
    """Write `entries` to `path` as `.steward/keys-inventory.yaml`-shaped YAML.

    Creates parent directories as needed. `yaml.safe_dump` only.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "identities": [
            {
                "name": e.name,
                "scope": e.scope,
                "provenance": e.provenance,
                "status": e.status,
                "last_rotated": e.last_rotated,
                "identity_path": e.identity_path,
                "secrets": list(e.secrets),
            }
            for e in entries
        ]
    }
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(document, f, sort_keys=False)


def generate_identity(output_path: str | Path) -> str:
    """`age-keygen -o output_path`; returns the newly generated identity's
    PUBLIC key (never its secret content).

    Raises `ValueError` for a `-` `output_path` (mirrors `_reject_dash`'s
    rationale for `age`'s own stdin/stdout sentinel), propagates
    `subprocess.CalledProcessError` on a non-zero `age-keygen` exit (e.g. the
    output path already exists and refuses overwrite), and raises
    `RuntimeError` if `age-keygen` exits 0 but emits no ``Public key: ``
    line on stderr (an unexpected shape this wrapper does not silently
    tolerate).
    """
    _reject_dash("output", output_path)
    result = subprocess.run(
        ["age-keygen", "-o", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
        errors="replace",
        stdin=subprocess.DEVNULL,
    )
    try:
        pubkey_line = next(
            line for line in result.stderr.splitlines() if line.startswith("Public key: ")
        )
    except StopIteration:
        raise RuntimeError(
            "age-keygen exited 0 but wrote no 'Public key: ' line to stderr "
            f"(stderr={result.stderr!r})"
        ) from None
    return pubkey_line.removeprefix("Public key: ")


def rotate_identity(
    inventory_path: str | Path, *, scope: str, new_identity_path: str | Path
) -> KeyIdentityEntry:
    """Rotate the `issued`/`active` identity for `scope`.

    Generates a fresh `age` identity at `new_identity_path`, re-encrypts
    every secret path the current active entry lists (decrypt under the old
    identity, encrypt under the new one, staged entirely through a private
    `tempfile.TemporaryDirectory` — plaintext never lands anywhere durable),
    then rewrites the inventory: the old entry becomes `status="retired"`
    and a NEW entry (same `scope`, an incremented generation `name`) is
    appended as `status="active"`. Every secret decrypts under the new
    identity when this returns; none decrypts under the old one any more,
    because each `.age` file at that path has been overwritten in place.

    Raises `InventoryError` if no `issued`/`active` entry exists for `scope`
    (covers: no entry at all, an `observed` entry, or an already-`retired`
    one), `ValueError` for a `-` `new_identity_path`, and propagates
    `subprocess.CalledProcessError` from `age-keygen`/`age` — never
    swallowed. A failure partway through re-encrypting a multi-secret scope
    leaves the inventory UNCHANGED (still pointing at the old, still-valid
    identity) and the already-processed secrets re-encrypted — a known,
    deliberately unsolved non-atomicity (see this story's spec, "Never").
    """
    _reject_dash("new_identity_path", new_identity_path)
    entries = load_inventory(inventory_path)

    active: KeyIdentityEntry | None = None
    for entry in entries:
        if entry.scope == scope and entry.provenance == "issued" and entry.status == "active":
            active = entry
            break
    if active is None:
        raise InventoryError(
            f"rotate: no issued/active identity found for scope {scope!r} in "
            f"{inventory_path}"
        )
    if not active.identity_path:
        raise InventoryError(
            f"rotate: identity {active.name!r} (scope {scope!r}) has no "
            "identity_path recorded — cannot decrypt its secrets"
        )

    new_pubkey = generate_identity(new_identity_path)

    with tempfile.TemporaryDirectory(prefix="steward-keys-rotate-") as tmpdir:
        staging = Path(tmpdir)
        for index, secret_path_str in enumerate(active.secrets):
            secret_path = Path(secret_path_str)
            staged_plaintext = staging / f"secret-{index}"
            decrypt_file(secret_path, identity=active.identity_path, output=staged_plaintext)
            encrypt_file(staged_plaintext, recipient=new_pubkey, output=secret_path)

    same_scope_count = sum(1 for e in entries if e.scope == scope)
    generation = same_scope_count + 1
    new_name = scope if generation == 1 else f"{scope}-{generation}"
    now = datetime.now(timezone.utc).isoformat()

    retired = KeyIdentityEntry(
        name=active.name,
        scope=active.scope,
        provenance=active.provenance,
        status="retired",
        last_rotated=active.last_rotated,
        identity_path=active.identity_path,
        secrets=active.secrets,
    )
    new_entry = KeyIdentityEntry(
        name=new_name,
        scope=scope,
        provenance="issued",
        status="active",
        last_rotated=now,
        identity_path=str(new_identity_path),
        secrets=active.secrets,
    )

    updated = tuple(retired if e is active else e for e in entries) + (new_entry,)
    save_inventory(inventory_path, updated)
    return new_entry


# ── Inventory display (FR-5/NFR-7, Story 1.5) ───────────────────────────────


def _entry_to_dict(entry: KeyIdentityEntry) -> dict[str, object]:
    """`entry`'s existing fields only — `identity_path`/`secrets` are
    filesystem pointers (Story 1.4's Design Notes), never key material or
    file content. This function never opens either path."""
    return {
        "name": entry.name,
        "scope": entry.scope,
        "provenance": entry.provenance,
        "status": entry.status,
        "last_rotated": entry.last_rotated,
        "identity_path": entry.identity_path,
        "secrets": list(entry.secrets),
    }


def format_inventory(entries: tuple[KeyIdentityEntry, ...], *, as_json: bool) -> str:
    """Render `entries` for `steward keys list`.

    `as_json=True`: a JSON array, one object per entry (all fields) —
    `[]` for an empty inventory, the correct machine-parseable empty state.
    `as_json=False`: an aligned text table (name/scope/provenance/status/
    last_rotated); a plain sentence for an empty inventory.

    Reads only `KeyIdentityEntry`'s own fields — never opens `identity_path`
    or any `secrets` entry, so a raw secret value cannot appear in either
    format (NFR-7; `tests/meta/test_invariants.py`'s
    `test_keys_list_output_never_contains_a_planted_secret_value` proves
    this by execution, not just by this docstring's claim).
    """
    if as_json:
        return json.dumps([_entry_to_dict(e) for e in entries], indent=2)
    if not entries:
        return "keys list: no identities in the inventory"
    header = f"{'NAME':<20} {'SCOPE':<20} {'PROVENANCE':<10} {'STATUS':<8} LAST_ROTATED"
    lines = [header]
    for e in entries:
        lines.append(
            f"{e.name:<20} {e.scope:<20} {e.provenance:<10} {e.status:<8} {e.last_rotated or '-'}"
        )
    return "\n".join(lines)


# ── KeysDuty (Duty-protocol adapter) ────────────────────────────────────────

_KEYS_VERBS: tuple[str, ...] = ("encrypt", "decrypt", "rotate", "list")


class KeysDuty:
    """The real `keys` duty — dispatches `encrypt`/`decrypt` onto the `age`
    subprocess primitives above.

    Bare `steward keys` (no verb) reaches this adapter with no ``keys_verb``
    and degrades to `DutyResult(ok=True, ...)` naming the available verbs
    (AD-7 — dispatch never crashes on a missing/unrecognized verb). Via the
    CLI that is the only path into the degrade branch — argparse rejects an
    unknown verb with a usage error before dispatch — so the
    ``verb not in _KEYS_VERBS`` guard otherwise protects programmatic
    callers handing this adapter an arbitrary namespace. `age` failing
    (bad identity, bad file) is caught here as `subprocess.CalledProcessError`,
    and a rejected `-` sentinel path as `ValueError` — both reported as
    duty-level failures (bad input, not a broken Steward), never conflated
    with an internal crash (AD-8: that boundary is `cli.main()`'s alone).
    """

    name = "keys"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "keys_verb", None)
        if verb not in _KEYS_VERBS:
            return DutyResult(
                ok=True,
                summary=f"keys: available verbs are {', '.join(_KEYS_VERBS)}",
            )
        try:
            if verb == "encrypt":
                encrypt_file(ns.file, recipient=ns.recipient, output=ns.output)
            elif verb == "decrypt":
                decrypt_file(ns.file, identity=ns.identity, output=ns.output)
            elif verb == "rotate":
                inventory_path = ns.inventory or default_inventory_path()
                entry = rotate_identity(
                    inventory_path, scope=ns.scope, new_identity_path=ns.new_identity
                )
                # Names the new entry and where its identity file lives —
                # never the public key or any secret content (Boundaries &
                # Constraints: rotate never prints a secret value).
                return DutyResult(
                    ok=True,
                    summary=(
                        f"keys rotate: scope {ns.scope!r} now active as "
                        f"{entry.name!r} (identity at {entry.identity_path})"
                    ),
                )
            else:  # verb == "list"
                inventory_path = ns.inventory or default_inventory_path()
                entries = load_inventory(inventory_path)
                return DutyResult(ok=True, summary=format_inventory(entries, as_json=ns.json))
        except ValueError as exc:
            return DutyResult(ok=False, summary=f"keys {verb}: {exc}")
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            return DutyResult(
                ok=False,
                summary=f"keys {verb}: age exited {exc.returncode}: {stderr}",
            )
        return DutyResult(ok=True, summary=f"keys {verb}: wrote {ns.output}")
