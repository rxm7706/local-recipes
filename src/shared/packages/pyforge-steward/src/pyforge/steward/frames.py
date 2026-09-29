"""In-repo Frame preflight (Story 53.2 / 53.5 / 53.6, spec-intelligence-hub CAP-2).

Checks the nine tracked Frames under ``docs/foundry/frames/``. Git is the store.

**Identity is ``identifier``, not ``name`` (Story 53.6).** v0.3 §4.2.1 makes
``identifier`` the one mandatory identity element and says it SHOULD be a URI or
a ``qualified-ref`` (``publisher "/" frame-name``, §5.3); ``name`` aliases
``title``, which the element profile marks *MUST NOT be slug-constrained* — a
human label, not a key. Keying this preflight off ``name`` therefore keyed it
off the wrong element, and off one the estate's own branding law wants to read
``PyForge Steward`` rather than a slug. Frames are now ``pyforge/company`` and
``pyforge/<station>``.

``type`` must start with the word ``frame`` (v0.3 §6.2.1; ``frame [0.2]`` and
a bare ``frame`` both pass). **The nine tracked Frames are bare ``type: frame``
(Story 64.1):** the draft's 09-14 revision says it "carries no version number
until a release assigns one", so ``frame [0.3]`` stamped a version that does
not exist. Station Frames must ``inherits`` the Company Frame.
``name``/``inherits`` are the spellings v0.3 *requires* of a Markdown writer
(§6.2.1 aliases: ``name`` denotes ``title``, ``inherits`` denotes
``composition``) — do not "modernize" them to the model-layer names, which
belong to the YAML/JSON encodings only.

``--upstream-check`` (Story 64.1, spec-pyforge-steward CAP-6 (c)) fetches
openteams-ai/frame-spec at the SHA pinned in ``docs/foundry/frames/upstream-pin.yaml``
into a temporary directory and runs *its* ``tools/validate_frame.py`` over our
Frames and ``--check-profile`` over ``conformance-profile.yaml``. The upstream
tool is never vendored and nothing is ever written upstream; the pin is the one
declared source. Exit ``0`` all OK, ``1`` upstream reported a FAIL, ``2`` the
check could not run (no git, no network, bad pin) — never a silent green. Opt-in
(``pixi run -e pyforge-steward frame-upstream-check``); joins no aggregate.

Not a detector and not a second PR verdict — Warden stays the sole gate.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

FRAMES_RELATIVE = Path("docs/foundry/frames")
UPSTREAM_PIN_RELATIVE = FRAMES_RELATIVE / "upstream-pin.yaml"
CONFORMANCE_PROFILE_RELATIVE = FRAMES_RELATIVE / "conformance-profile.yaml"
EXIT_OK, EXIT_FAIL, EXIT_COULD_NOT_RUN = 0, 1, 2
COMPANY_IDENTIFIER = "pyforge/company"
PUBLISHER = "pyforge"
STATION_TOKENS: tuple[str, ...] = (
    "herald",
    "marshal",
    "atlas",
    "warden",
    "mason",
    "doctor",
    "scribe",
    "steward",
)
EXPECTED_COUNT = 1 + len(STATION_TOKENS)
REQUIRED_FIELDS: tuple[str, ...] = (
    "type",
    "identifier",
    "name",
    "description",
    "visibility",
    "maintainer",
)
#: v0.3 §6.2.1 — "A writer MUST emit a sequence" for a repeatable element.
#: A scalar is legal to *read* and stays accepted on the way in; emitting one
#: is what the spec forbids, and these files are ours to write.
SEQUENCE_FIELDS: tuple[str, ...] = ("maintainer", "inherits")
FRONTMATTER_SPLIT = "---"


def _type_is_frame(value: object) -> bool:
    """v0.3 draft §6.2.1: type MUST begin with the word ``frame``."""
    if not isinstance(value, str) or not value.strip():
        return False
    return value.strip().split()[0] == "frame"


@dataclass(frozen=True)
class FrameDoc:
    path: Path
    fields: dict[str, Any]
    body: str


@dataclass(frozen=True)
class FrameFinding:
    path: Path
    code: str
    message: str


@dataclass
class FramePreflightReport:
    frames: list[FrameDoc] = field(default_factory=list)
    findings: list[FrameFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings


def default_frames_root(repo_root: Path) -> Path:
    return repo_root / FRAMES_RELATIVE


def parse_frame_markdown(path: Path) -> tuple[dict[str, Any] | None, str, str | None]:
    """Return ``(frontmatter, body, parse_error)``."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith(FRONTMATTER_SPLIT):
        return None, text, "missing YAML frontmatter"
    rest = text[len(FRONTMATTER_SPLIT) :]
    if rest.startswith("\n"):
        rest = rest[1:]
    closer = rest.find(f"\n{FRONTMATTER_SPLIT}\n")
    if closer < 0:
        closer = rest.find(f"\n{FRONTMATTER_SPLIT}\r\n")
    if closer < 0:
        return None, text, "unclosed YAML frontmatter"
    raw = rest[:closer]
    body = rest[closer + len(f"\n{FRONTMATTER_SPLIT}\n") :]
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, body, f"invalid YAML frontmatter: {exc}"
    if not isinstance(loaded, dict):
        return None, body, "frontmatter is not a mapping"
    return loaded, body, None


def discover_frame_paths(frames_root: Path) -> list[Path]:
    if not frames_root.is_dir():
        return []
    return sorted(p for p in frames_root.rglob("*.frame.md") if p.is_file())


def _as_inherits_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Sequence) and not isinstance(value, (bytes, str)):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _resolve_inherit(
    ref: str,
    child: Path,
    by_name: dict[str, FrameDoc],
) -> FrameDoc | None:
    if ref in by_name:
        return by_name[ref]
    candidate = (child.parent / ref).resolve()
    for doc in by_name.values():
        if doc.path.resolve() == candidate:
            return doc
    return None


def preflight_frames(repo_root: Path, *, frames_root: Path | None = None) -> FramePreflightReport:
    root = frames_root if frames_root is not None else default_frames_root(repo_root)
    report = FramePreflightReport()
    paths = discover_frame_paths(root)
    if len(paths) != EXPECTED_COUNT:
        report.findings.append(
            FrameFinding(
                path=root,
                code="count",
                message=(
                    f"expected exactly {EXPECTED_COUNT} *.frame.md files "
                    f"(one company + eight stations); found {len(paths)}"
                ),
            )
        )

    for path in paths:
        fields, body, err = parse_frame_markdown(path)
        if err is not None or fields is None:
            report.findings.append(FrameFinding(path=path, code="parse", message=err or "parse failed"))
            continue
        report.frames.append(FrameDoc(path=path, fields=fields, body=body))
        for key in REQUIRED_FIELDS:
            raw = fields.get(key)
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                report.findings.append(
                    FrameFinding(
                        path=path,
                        code="missing-field",
                        message=f"required field {key!r} is missing or empty",
                    )
                )
        type_val = fields.get("type")
        if isinstance(type_val, str) and type_val.strip() and not _type_is_frame(type_val):
            report.findings.append(
                FrameFinding(
                    path=path,
                    code="type",
                    message=(f"type must begin with the word 'frame' (v0.3 draft), got {type_val!r}"),
                )
            )
        for key in SEQUENCE_FIELDS:
            raw = fields.get(key)
            if raw is not None and isinstance(raw, str):
                report.findings.append(
                    FrameFinding(
                        path=path,
                        code="scalar-repeatable",
                        message=(
                            f"{key!r} is repeatable — v0.3 §6.2.1 requires a writer "
                            f"to emit a sequence, got the scalar {raw!r}"
                        ),
                    )
                )

    by_identifier: dict[str, FrameDoc] = {}
    for doc in report.frames:
        ident = doc.fields.get("identifier")
        if isinstance(ident, str) and ident.strip():
            by_identifier.setdefault(ident.strip(), doc)

    company = by_identifier.get(COMPANY_IDENTIFIER)
    if company is None:
        report.findings.append(
            FrameFinding(
                path=root,
                code="company",
                message=(f"company Frame with identifier {COMPANY_IDENTIFIER!r} is required"),
            )
        )
        return report

    expected_station_ids = {f"{PUBLISHER}/{token}" for token in STATION_TOKENS}
    seen_stations: set[str] = set()
    for doc in report.frames:
        ident = doc.fields.get("identifier")
        ident = ident.strip() if isinstance(ident, str) else ident
        if ident == COMPANY_IDENTIFIER:
            if _as_inherits_list(doc.fields.get("inherits")):
                report.findings.append(
                    FrameFinding(
                        path=doc.path,
                        code="company-inherits",
                        message="company Frame must not inherit another Frame",
                    )
                )
            continue
        if ident not in expected_station_ids:
            report.findings.append(
                FrameFinding(
                    path=doc.path,
                    code="unexpected-identifier",
                    message=f"unexpected Frame identifier {ident!r}",
                )
            )
            continue
        seen_stations.add(str(ident))
        refs = _as_inherits_list(doc.fields.get("inherits"))
        if not refs:
            report.findings.append(
                FrameFinding(
                    path=doc.path,
                    code="inherits",
                    message=f"station Frame must inherit {COMPANY_IDENTIFIER!r}",
                )
            )
            continue
        resolved = [_resolve_inherit(ref, doc.path, by_identifier) for ref in refs]
        if not any(
            parent is not None and str(parent.fields.get("identifier", "")).strip() == COMPANY_IDENTIFIER
            for parent in resolved
        ):
            report.findings.append(
                FrameFinding(
                    path=doc.path,
                    code="inherits",
                    message=(
                        f"station Frame inherits {refs!r} but none resolve to the company Frame {COMPANY_IDENTIFIER!r}"
                    ),
                )
            )

    missing = expected_station_ids - seen_stations
    if missing:
        report.findings.append(
            FrameFinding(
                path=root,
                code="stations",
                message=f"missing station Frame(s): {', '.join(sorted(missing))}",
            )
        )
    return report


def format_report(report: FramePreflightReport) -> str:
    if report.ok:
        return (
            f"frame-preflight: ok — {len(report.frames)} Frames "
            f"(company {COMPANY_IDENTIFIER} + {len(STATION_TOKENS)} stations)"
        )
    lines = [f"frame-preflight: {len(report.findings)} finding(s)"]
    for finding in report.findings:
        lines.append(f"  [{finding.code}] {finding.path}: {finding.message}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Story 64.1 -- upstream check at the pinned SHA
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UpstreamPin:
    repository: str
    sha: str
    entrypoint: str
    pr: int | None = None


def load_upstream_pin(repo_root: Path) -> UpstreamPin:
    """Read the one declared pin. Raises ``ValueError`` on a malformed file so
    a bad pin is a could-not-run, never a pass."""
    path = repo_root / UPSTREAM_PIN_RELATIVE
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: pin is not a mapping")
    validator = data.get("validator")
    repository = data.get("repository")
    if not isinstance(validator, dict) or not isinstance(repository, str):
        raise ValueError(f"{path}: needs `repository:` and a `validator:` mapping")
    sha = validator.get("sha")
    entrypoint = validator.get("entrypoint", "tools/validate_frame.py")
    if not isinstance(sha, str) or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError(f"{path}: validator.sha must be a full 40-hex commit SHA")
    if not isinstance(entrypoint, str) or not entrypoint:
        raise ValueError(f"{path}: validator.entrypoint must be a relative path")
    pr = validator.get("pr")
    return UpstreamPin(
        repository=repository,
        sha=sha,
        entrypoint=entrypoint,
        pr=pr if isinstance(pr, int) else None,
    )


def fetch_pinned_checkout(pin: UpstreamPin, dest: Path, *, run=subprocess.run) -> None:
    """A read-only, depth-1 fetch of exactly the pinned commit into ``dest``.
    No branch is tracked and nothing is ever pushed."""
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git is not on PATH")
    dest.mkdir(parents=True, exist_ok=True)
    for argv in (
        [git, "init", "-q", str(dest)],
        [git, "-C", str(dest), "remote", "add", "origin", pin.repository],
        [git, "-C", str(dest), "fetch", "-q", "--depth", "1", "origin", pin.sha],
        [git, "-C", str(dest), "checkout", "-q", "--detach", "FETCH_HEAD"],
    ):
        proc = run(argv, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"{' '.join(argv[1:4])} failed: {proc.stderr.strip() or proc.stdout.strip()}")


def upstream_check(
    repo_root: Path,
    *,
    frames_root: Path | None = None,
    run=subprocess.run,
    fetch=fetch_pinned_checkout,
) -> tuple[int, str]:
    """Run upstream's validator, at the pin, over our Frames and our profile.

    Returns ``(exit_code, report_text)`` with the frozen domain
    ``{EXIT_OK, EXIT_FAIL, EXIT_COULD_NOT_RUN}``.
    """
    root = frames_root or default_frames_root(repo_root)
    try:
        pin = load_upstream_pin(repo_root)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return EXIT_COULD_NOT_RUN, f"frame-upstream-check: could not run — {exc}"
    lines = [
        f"frame-upstream-check: {pin.repository}"
        + (f"#{pin.pr}" if pin.pr else "")
        + f" @ {pin.sha[:10]} ({pin.entrypoint})"
    ]
    with tempfile.TemporaryDirectory(prefix="frame-spec-") as tmp:
        checkout = Path(tmp) / "frame-spec"
        try:
            fetch(pin, checkout)
        except (RuntimeError, OSError) as exc:
            return EXIT_COULD_NOT_RUN, "\n".join([*lines, f"could not run — fetch failed: {exc}"])
        tool = checkout / pin.entrypoint
        if not tool.is_file():
            return EXIT_COULD_NOT_RUN, "\n".join(
                [*lines, f"could not run — {pin.entrypoint} is not in the pinned tree"]
            )
        targets = [str(p) for p in discover_frame_paths(root)]
        legs: list[tuple[str, list[str]]] = [("frames", targets)]
        profile = repo_root / CONFORMANCE_PROFILE_RELATIVE
        if profile.is_file():
            legs.append(("profile", ["--check-profile", str(profile)]))
        else:
            lines.append(f"profile: {CONFORMANCE_PROFILE_RELATIVE} absent — leg skipped")
        worst = EXIT_OK
        for name, args in legs:
            proc = run(
                [sys.executable, str(tool), *args],
                capture_output=True,
                text=True,
                cwd=str(checkout),
            )
            out = (proc.stdout or "").rstrip()
            err = (proc.stderr or "").rstrip()
            lines.append(f"--- {name} (exit {proc.returncode})")
            if out:
                lines.append(out)
            if err:
                lines.append(err)
            if proc.returncode not in (0, 1):
                worst = max(worst, EXIT_COULD_NOT_RUN)
            elif proc.returncode == 1:
                worst = max(worst, EXIT_FAIL)
    return worst, "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="frame-preflight",
        description=(
            "In-repo Frame preflight (v0.2 + v0.3 draft) for docs/foundry/frames/. "
            "Not a detector; Warden stays the sole PR verdict."
        ),
    )
    parser.add_argument(
        "--repo",
        default=".",
        metavar="PATH",
        help="repository root (default: cwd)",
    )
    parser.add_argument(
        "--upstream-check",
        action="store_true",
        help=(
            "instead of the in-repo preflight, fetch openteams-ai/frame-spec at the SHA "
            "pinned in docs/foundry/frames/upstream-pin.yaml into a temp dir and run ITS "
            "validate_frame.py over our Frames and --check-profile over our profile "
            "(exit 0 ok / 1 upstream FAIL / 2 could not run). Read-only; never vendored."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    repo_root = Path(ns.repo).resolve()
    if ns.upstream_check:
        code, text = upstream_check(repo_root)
        print(text)
        return code
    report = preflight_frames(repo_root)
    print(format_report(report))
    return EXIT_OK if report.ok else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
