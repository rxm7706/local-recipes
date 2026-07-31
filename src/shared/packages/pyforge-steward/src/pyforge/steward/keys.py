"""Steward's `keys` duty-adapter module (AD-1/AD-2) — Epic 1's single file.

Story 1.2 slice: a host-scoped credential resolver (FR-7) and a drift-detection
primitive (FR-4) that AST-scans a Python source file for the historical
unconditional-injection shape `_http.py` had before commit ``a4137cdfa3``.

Both pieces delegate entirely to `.claude/skills/conda-forge-expert/scripts/
_http.py`'s ``auth_headers_for`` — this module decides only *host membership*
and *whether a function's header-attachment is gated*; it never builds its own
request/header logic (AD-1, AD-2: delegate, never reimplement). Stories 1.3-1.7
extend this same file (the architecture's single duty-adapter-module design for
Epic 1) rather than splitting it into a subpackage. No CLI verb is wired to
this yet — `cli.py`'s `resolve_duty("keys")` still returns `NullDuty` until
Story 1.6.
"""

from __future__ import annotations

import ast
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

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
