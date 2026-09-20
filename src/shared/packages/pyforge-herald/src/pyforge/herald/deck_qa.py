"""Deck visual-QA gate report interface (Story 14.1) + the headless-render
gate (Story 14.2) + the image-slot scan gate (Story 14.3).

Herald's deck pipeline needs a shared, extensible way for visual-QA gates
-- the headless-render gate and the image-slot scan gate below, and three
parked ``.pptx``-contingent gates -- to report findings against one deck
slug. This module defines that report's JSON-round-trippable schema, the
``run()`` entrypoint that executes a caller-supplied gate mapping without
deciding what any individual gate checks, and (as of Story 14.2) the first
real gate: ``render_gate``, registered under ``DEFAULT_GATES["render"]``,
joined in Story 14.3 by ``image_slot_gate`` under
``DEFAULT_GATES["image-slot"]``.

``DEFAULT_GATES`` shipped empty in Story 14.1 on purpose: each later story
adds one entry here (a ``GateFn`` registered under a gate id) with zero
change to this module's public shape, to ``run()``'s signature, or to
``cli.py`` -- the whole point of the interface existing ahead of any real
gate, now proven by both ``render_gate``'s and ``image_slot_gate``'s own
additions.

**A gate failure is isolated, never fatal to the report.** A gate raising
an exception is a realistic first failure mode (a missing browser binary,
a malformed deck source, a bug in the gate itself) and must not deny an
operator every OTHER gate's results just because one gate broke -- so
``run()`` catches per-gate, recording ``GateResult(status="error", ...)``
for that id alone. ``run()`` itself never raises because of a gate's own
failure.

**``GateResult`` never repeats its own gate id.** The id lives only as the
dict key in ``DeckQaReport.gates`` -- a ``gate_id`` field on ``GateResult``
too would let a hand-edited or buggy report disagree with itself (the key
says one id, the field says another) with no way to say which is right.
Mirrors ``state.py``'s AD-6 discipline: ``to_dict``/``parse_report`` round-
trip the schema exactly, and ``parse_report`` rejects any missing/
unrecognized field or bad ``status`` value by raising ``errors.HeraldError``
rather than silently dropping or coercing it.
"""

from __future__ import annotations

import functools
import http.server
import json
import math
import re
import shutil
import socketserver
import threading
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import errors


@dataclass(frozen=True)
class Finding:
    """One gate's flagged problem on one slide."""

    slide_id: str
    message: str


@dataclass(frozen=True)
class GateResult:
    """One gate's outcome: ``status`` is ``"ok"`` or ``"error"``.

    ``error`` carries the caught exception's message when ``status`` is
    ``"error"`` (``run()`` sets it; a gate function itself never needs to
    populate it directly) and stays ``None`` for ``"ok"``. ``artifacts`` is
    a list of paths/identifiers a gate produced (e.g. a rendered PNG) --
    this story defines the slot but writes nothing to disk itself; where
    such artifacts live is Story 14.2's decision."""

    status: str
    findings: list[Finding] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class DeckQaReport:
    """The whole QA report for one deck slug: every gate's result, keyed by
    gate id (the key is the sole owner of the id -- see module docstring)."""

    slug: str
    gates: dict[str, GateResult]


@dataclass(frozen=True)
class GateContext:
    """What every gate function receives: the deck slug and the repo root
    to resolve deck sources against. 14.2/14.3 may extend this dataclass
    (they edit this same file) as real gates need more inputs."""

    slug: str
    repo_root: Path


GateFn = Callable[[GateContext], GateResult]
"""One gate: a function from a ``GateContext`` to its own ``GateResult``."""


DEFAULT_GATES: dict[str, GateFn] = {}
"""Shipped empty in Story 14.1 -- see module docstring. A plain module-level
dict, not a decorator-based registry: every gate lives in this one file per
the epic's Surface lines, so there is no cross-module registration to
build. Story 14.2 populates the first real entry (``"render"``, below) with
zero change to this dict's shape, ``run()``'s signature, or ``cli.py``."""


# === render_gate (Story 14.2) ================================================
#
# Drives headless Chromium through every `#/<n>` slide of a built deck
# (`presentations/<slug>/dist/`), screenshotting each to
# `.herald/deck-qa/<slug>/render/` and composing a Pillow contact sheet --
# evidence a reviewer looks at instead of trusting a clean build (this
# story's spec: Intent). Mirrors `pyforge-doctor/sources/board.py`'s own
# `_serve_layout_dir` (ephemeral loopback static server) and
# `_run_check_layout` (Chromium-launch-fallback chain, per-item isolation,
# `_suppress_close` teardown) patterns -- see that module for the full
# rationale behind each pattern. This module does NOT import from
# `pyforge.doctor` (a different station's package); the patterns are
# re-implemented locally here per this story's own Code Map.

_RENDER_VIEWPORT = {"width": 1920, "height": 1080}
_RENDER_LAUNCH_TIMEOUT_MS = 30_000
_RENDER_GOTO_TIMEOUT_MS = 20_000
_RENDER_SCREENSHOT_TIMEOUT_MS = 20_000


class _DeckQuietHandler(http.server.SimpleHTTPRequestHandler):
    """``SimpleHTTPRequestHandler`` logs every GET to stderr, which buries
    whatever this gate is supposed to report. Ported from board.py's own
    ``_LayoutQuietHandler``; renamed only for this module's naming
    convention."""

    def log_message(self, *_args):  # noqa: D102
        pass


def _serve_dist_dir(directory: Path) -> tuple[socketserver.TCPServer, int]:
    """Serve a built deck's ``dist/`` over an ephemeral loopback port --
    ported from board.py's own ``_serve_layout_dir``. Chromium needs a real
    HTTP origin, not ``file://``: the deck is a Vite bundle with
    dynamically-imported JS chunks, and Chromium blocks cross-origin
    fetch/module-import under ``file://`` (this story's spec: Boundaries &
    Constraints)."""
    handler = functools.partial(_DeckQuietHandler, directory=str(directory))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def _suppress_close(close: Callable[[], None]) -> None:
    """Run a cleanup callable, swallowing anything it raises -- ported from
    board.py's own ``_suppress_close``: a browser/socket that fails to shut
    down is not a render verdict, and letting it propagate would replace
    every already-captured slide with one vacuous error. Catches
    ``SystemExit`` too, not just ``Exception``: this module's own per-slide
    capture loop below documents that playwright's internals have raised
    ``SystemExit`` live, and this function tears down those same playwright
    objects (``browser.close``, ``page.close``) -- the docstring's own
    "swallowing anything it raises" promise must hold for that case too."""
    try:
        close()
    except Exception, SystemExit:  # noqa: BLE001, S110 -- see the
        # docstring above; a failed teardown must never be able to change
        # what this gate reports.
        pass


_RESERVED_SLIDE_IDS = frozenset({"contact-sheet"})


def _single_path_segment(candidate: object) -> bool:
    """``True`` only for a string that is exactly one path segment -- no
    ``/`` or ``\\``, no ``..``, no empty/`.`-only component. Guards every
    id/slug this module turns into a filesystem path (a slide id from
    ``manifest.json``, or ``context.slug`` itself) against writing/reading
    outside the directory that name was supposed to select (Review Triage
    Log).

    Checks the raw string for a separator directly rather than routing
    through ``Path(candidate).parts``: ``Path`` normalizes away a leading
    ``./`` or trailing ``/.``, so ``"./.."`` measures as the single part
    ``".."`` post-normalization even though the raw string contains a
    literal ``/`` -- a disguised traversal string the previous
    ``len(Path(...).parts) == 1`` check let straight through (Review pass,
    second round). Also rejects a non-``str`` candidate outright, matching
    ``_slide_id``'s own ``isinstance`` guard, so a caller passing something
    other than a string gets this function's own ``False`` -> the caller's
    documented error, not a raw ``TypeError`` out of ``Path()``."""
    if not isinstance(candidate, str) or not candidate:
        return False
    if candidate in (".", ".."):
        return False
    return "/" not in candidate and "\\" not in candidate


def _slide_id(entry: object, index: int) -> str:
    """``manifest[index]["id"]`` when present and safe, else a positional
    fallback.

    The manifest is documented (this story's spec: Boundaries & Constraints)
    as a flat JSON array whose entries always carry a stable string ``id``,
    but a malformed OR path-unsafe entry must still resolve to SOME slide id
    so its own capture failure can be recorded as an isolated ``Finding``
    rather than raise out of the whole gate or escape ``render_dir``."""
    if isinstance(entry, dict):
        raw_id = entry.get("id")
        if isinstance(raw_id, str) and _single_path_segment(raw_id):
            return raw_id
    return f"slide-{index + 1}"


def _build_contact_sheet(png_paths: list[Path], out_path: Path) -> None:
    """A Pillow grid composite of every captured slide, labeled by slide id
    -- the evidence a reviewer looks at instead of trusting a clean build.

    Skipped (no file written) when ``png_paths`` is empty -- a contact sheet
    of zero images is not evidence of anything, and every I/O matrix row
    where nothing captures also records no ``"contact-sheet"`` artifact."""
    if not png_paths:
        return
    from PIL import Image, ImageDraw

    thumb_w, thumb_h, label_h = 320, 180, 20
    cols = math.ceil(math.sqrt(len(png_paths)))
    rows = math.ceil(len(png_paths) / cols)
    cell_w, cell_h = thumb_w, thumb_h + label_h
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(png_paths):
        with Image.open(path) as source:
            thumb = source.convert("RGB").resize((thumb_w, thumb_h))
        col, row = index % cols, index // cols
        x, y = col * cell_w, row * cell_h
        sheet.paste(thumb, (x, y))
        draw.text((x + 4, y + thumb_h + 2), path.stem, fill="black")
    sheet.save(out_path)


def render_gate(context: GateContext) -> GateResult:
    """Drive headless Chromium through every ``#/<n>`` slide of
    ``presentations/<slug>/dist/``, screenshotting each to
    ``.herald/deck-qa/<slug>/render/<slide-id>.png`` and composing a contact
    sheet. See this story's spec (Intent, Boundaries & Constraints, Design
    Notes) for the full rationale.

    Report-only: never runs a build, never mutates deck sources.
    ``.herald/deck-qa/<slug>/render/`` is ``rmtree``'d then recreated once
    Chromium is confirmed launchable (not any earlier -- Review pass, second
    round: wiping it before that point meant a "no usable chromium" failure
    deleted the previous run's own evidence with nothing to replace it), so
    a shrunk manifest never leaves a stale PNG looking current.

    Raises on a genuinely unusable environment -- ``dist/`` absent,
    ``manifest.json`` absent/malformed, an unusable ``playwright`` install,
    or no launchable Chromium -- which ``run()``'s own per-gate isolation
    (Story 14.1) turns into ``GateResult(status="error", ...)`` for the
    ``"render"`` gate id alone; every other gate is unaffected. A single
    slide's own ``goto``/``screenshot`` failure is isolated instead: it
    becomes one ``Finding`` and every other slide still captures, mirroring
    board.py's per-width isolation in ``_run_check_layout`` -- the gate's own
    ``status`` stays ``"ok"`` even when every slide fails this way."""
    if not _single_path_segment(context.slug):
        raise RuntimeError(f"invalid slug {context.slug!r}")

    deck_dir = context.repo_root / "presentations" / context.slug
    dist_dir = deck_dir / "dist"
    manifest_path = deck_dir / "src" / "slides" / "manifest.json"

    if not dist_dir.is_dir():
        raise RuntimeError(f"{dist_dir} does not exist -- build the deck first (npm run build)")
    if not manifest_path.is_file():
        raise RuntimeError(f"{manifest_path} does not exist")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 -- surfaced as a clear render-gate error
        raise RuntimeError(f"cannot parse {manifest_path}: {exc}") from exc
    if not isinstance(manifest, list):
        raise RuntimeError(f"{manifest_path} must contain a JSON array")

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001 -- an unimportable/broken install
        # is "no usable Chromium" for this gate's purposes; see the I/O matrix.
        raise RuntimeError(f"playwright is not usable: {exc}") from exc

    render_dir = context.repo_root / ".herald" / "deck-qa" / context.slug / "render"

    httpd, port = _serve_dist_dir(dist_dir)
    findings: list[Finding] = []
    png_paths: list[Path] = []
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome", timeout=_RENDER_LAUNCH_TIMEOUT_MS)
            except Exception, SystemExit:  # noqa: BLE001 -- fall back to
                # bundled chromium, matching board.py's own fallback order
                # verbatim. SystemExit included for the same reason the
                # per-slide loop below catches it: playwright's own
                # internals have raised it live.
                try:
                    browser = p.chromium.launch(timeout=_RENDER_LAUNCH_TIMEOUT_MS)
                except (Exception, SystemExit) as exc:  # noqa: BLE001 -- no
                    # usable browser at all
                    raise RuntimeError(f"no usable chromium ({type(exc).__name__}): {exc}") from exc
            # Only now that Chromium is known launchable is it safe to wipe
            # the previous run's evidence (Review pass, second round):
            # wiping render_dir any earlier meant a "no usable chromium"
            # failure -- a documented, expected failure mode, see the I/O
            # matrix -- deleted the last known-good PNGs/contact-sheet with
            # nothing to replace them, working against this gate's whole
            # purpose of leaving a reviewer something to look at.
            if render_dir.exists():
                shutil.rmtree(render_dir)
            render_dir.mkdir(parents=True, exist_ok=True)
            seen_ids: set[str] = set(_RESERVED_SLIDE_IDS)
            try:
                for index, entry in enumerate(manifest):
                    slide_id = _slide_id(entry, index)
                    if slide_id in seen_ids:
                        # A duplicate manifest id (or one colliding with a
                        # reserved name like "contact-sheet") would otherwise
                        # silently overwrite an earlier slide's own PNG.
                        slide_id = f"{slide_id}-{index}"
                    seen_ids.add(slide_id)
                    try:
                        page = browser.new_page(viewport=_RENDER_VIEWPORT)
                        try:
                            page.goto(
                                f"http://127.0.0.1:{port}/#/{index + 1}",
                                wait_until="networkidle",
                                timeout=_RENDER_GOTO_TIMEOUT_MS,
                            )
                            out_path = render_dir / f"{slide_id}.png"
                            page.screenshot(
                                path=str(out_path),
                                timeout=_RENDER_SCREENSHOT_TIMEOUT_MS,
                            )
                            png_paths.append(out_path)
                        finally:
                            _suppress_close(page.close)
                    except (Exception, SystemExit) as exc:  # noqa: BLE001 --
                        # SystemExit: defense-in-depth against playwright's
                        # own internals raising it (board.py's per-width loop
                        # catches the identical pair after reproducing this
                        # live; a bare `except Exception` here would let it
                        # unwind the loop and discard every already-captured
                        # slide). One slide's own capture failure must not
                        # unwind the loop or the gate's own "ok" status
                        # (spec: Boundaries).
                        findings.append(Finding(slide_id=slide_id, message=str(exc)))
            finally:
                _suppress_close(browser.close)
    finally:
        _suppress_close(httpd.shutdown)
        _suppress_close(httpd.server_close)

    artifacts = [str(p) for p in png_paths]
    if png_paths:
        contact_sheet_path = render_dir / "contact-sheet.png"
        try:
            _build_contact_sheet(png_paths, contact_sheet_path)
        except Exception as exc:  # noqa: BLE001 -- a contact-sheet failure
            # (corrupt PNG, disk full) must not discard every already-
            # captured slide's own Finding/artifact -- the same masking
            # bug the per-slide isolation above exists to avoid.
            findings.append(Finding(slide_id="contact-sheet", message=str(exc)))
        else:
            artifacts.append(str(contact_sheet_path))

    return GateResult(status="ok", findings=findings, artifacts=artifacts)


DEFAULT_GATES["render"] = render_gate
"""Registers the render gate under id ``"render"`` -- the only production
change this story makes to ``DEFAULT_GATES``'s contents; its shape, and
``run()``'s own signature, are untouched (module docstring)."""


# === image_slot_gate (Story 14.3) ============================================
#
# Scans each manifest-listed slide's generated fragment
# (`presentations/<slug>/src/slides/fragments/<id>.html`) for an unfilled
# image-slot placeholder -- the CAP-2 half of "renders but doesn't prove it
# looks right" (this story's spec: Intent). Pure file scanning: no browser,
# no build, and (unlike `render_gate`) no `artifacts` of its own.
#
# Both patterns are case-insensitive: this gate exists partly to catch a tag
# extraction itself missed (this story's spec: Boundaries & Constraints, "raw
# unconverted tag"), and the extractor's own tag match is *also*
# case-sensitive, so a case-variant `<Image-Slot>` would otherwise slip past
# both stages. `_IMAGE_SLOT_TAG_RE` uses a lookahead, not `\b`, after
# "image-slot": `-` is a non-word character, so a bare `\b` there would also
# match an unrelated hyphenated custom element like `<image-slot-carousel>`
# (word/non-word transition right after "slot" regardless of what follows).

_IMAGE_SLOT_TAG_RE = re.compile(r"<image-slot(?=[\s/>])", re.IGNORECASE)
_IMAGE_SLOT_DIV_RE = re.compile(r'class="image-slot"', re.IGNORECASE)


def image_slot_gate(context: GateContext) -> GateResult:
    """Flag every manifest-listed slide whose generated fragment still
    contains an unfilled image-slot placeholder, in either its raw
    prototype spelling (``<image-slot ...>``) or its extractor-converted
    spelling (``class="image-slot"`` div). See this story's spec (Intent,
    Boundaries & Constraints, Design Notes) for the full rationale.

    Report-only: never mutates deck sources, never triggers extraction or a
    build. Produces no ``artifacts`` -- this gate needs no build and no
    browser, so there is nothing to leave on disk as evidence (Boundaries &
    Constraints).

    Raises on a genuinely unusable environment -- ``manifest.json``
    absent/malformed, or ``fragments/`` itself absent -- which ``run()``'s
    own per-gate isolation (Story 14.1) turns into
    ``GateResult(status="error", ...)`` for the ``"image-slot"`` gate id
    alone; every other gate is unaffected. A single slide's own fragment
    being missing or unreadable is isolated instead: it becomes one
    ``Finding`` and every other slide is still scanned, mirroring
    ``render_gate``'s own per-slide isolation -- the gate's own ``status``
    stays ``"ok"`` even when every slide is flagged this way."""
    if not _single_path_segment(context.slug):
        raise RuntimeError(f"invalid slug {context.slug!r}")

    deck_dir = context.repo_root / "presentations" / context.slug
    manifest_path = deck_dir / "src" / "slides" / "manifest.json"
    fragments_dir = deck_dir / "src" / "slides" / "fragments"

    if not manifest_path.is_file():
        raise RuntimeError(f"{manifest_path} does not exist")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 -- surfaced as a clear image-slot-gate error
        raise RuntimeError(f"cannot parse {manifest_path}: {exc}") from exc
    if not isinstance(manifest, list):
        raise RuntimeError(f"{manifest_path} must contain a JSON array")
    if not fragments_dir.is_dir():
        raise RuntimeError(f"{fragments_dir} does not exist -- run the extractor first (npm run extract)")

    findings: list[Finding] = []
    for index, entry in enumerate(manifest):
        slide_id = _slide_id(entry, index)
        fragment_path = fragments_dir / f"{slide_id}.html"
        try:
            html = fragment_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            # UnicodeDecodeError (a ValueError, not an OSError) is caught
            # alongside a missing/unreadable file: this per-slide isolation
            # must hold for a fragment that exists but is not valid UTF-8
            # too, or one bad file would error the whole gate instead of
            # isolating that slide (this story's spec: Boundaries &
            # Constraints).
            findings.append(
                Finding(
                    slide_id=slide_id,
                    message=f"cannot read {fragment_path}: {exc}",
                )
            )
            continue
        if _IMAGE_SLOT_TAG_RE.search(html) or _IMAGE_SLOT_DIV_RE.search(html):
            findings.append(
                Finding(
                    slide_id=slide_id,
                    message=f"unfilled image-slot placeholder in {fragment_path}",
                )
            )

    return GateResult(status="ok", findings=findings)


DEFAULT_GATES["image-slot"] = image_slot_gate
"""Registers the image-slot gate under id ``"image-slot"`` -- the only
production change this story makes to ``DEFAULT_GATES``'s contents; its
shape, and ``run()``'s own signature, are untouched (module docstring)."""


def run(slug: str, repo_root: Path, gates: Mapping[str, GateFn] | None = None) -> DeckQaReport:
    """Run every gate in ``gates`` against ``slug``/``repo_root`` and
    assemble the report. Pure computation over the supplied mapping: never
    writes to disk, never mutates deck sources, never triggers a rebuild.

    ``gates`` defaults to ``None`` and is resolved to ``DEFAULT_GATES``
    *inside* the call, not via a mutable default-argument value -- a
    default bound at def time would keep pointing at today's empty dict
    forever if a later story reassigns ``DEFAULT_GATES = {...}`` rather
    than mutating it in place. Reading the module attribute fresh on every
    call makes both update styles safe. A caller -- including a test
    proving the "add a third gate" extensibility claim -- can still supply
    its own mapping without touching shared state.

    A gate misbehaving is caught for that gate alone and recorded as
    ``GateResult(status="error", error=...)`` -- the remaining gates still
    run, and this function itself never raises because of one gate's own
    failure (module docstring). "Misbehaving" covers both a raised
    exception AND a gate returning something other than a well-formed
    ``GateResult`` (wrong type, an unrecognized ``status``, or a
    ``status``/``error`` pairing that violates the ``"error"`` <=>
    non-``None`` invariant ``parse_report`` also enforces) -- a gate that
    forgets its ``return`` or hands back a bespoke object is exactly as
    contained as one that raises, never silently corrupting the report."""
    if gates is None:
        gates = DEFAULT_GATES
    context = GateContext(slug=slug, repo_root=repo_root)
    results: dict[str, GateResult] = {}
    for gate_id, gate_fn in gates.items():
        try:
            result = gate_fn(context)
            if (
                not isinstance(result, GateResult)
                or result.status not in _GATE_STATUSES
                or (result.status == "error") != (result.error is not None)
            ):
                raise TypeError(
                    f"gate {gate_id!r} returned {result!r}, expected a "
                    f"GateResult with status in {sorted(_GATE_STATUSES)} and "
                    f"'error' set if and only if status is 'error'"
                )
            results[gate_id] = result
        except Exception as exc:  # noqa: BLE001 -- isolates one gate's failure
            results[gate_id] = GateResult(status="error", error=str(exc))
    return DeckQaReport(slug=slug, gates=results)


def to_dict(report: DeckQaReport) -> dict[str, Any]:
    """``report`` as a JSON-serializable dict -- the exact shape
    ``parse_report`` inverts. Delegates to ``dataclasses.asdict`` (mirrors
    ``state.py``'s own idiom): every field here is itself a dataclass,
    primitive, or a plain ``list``/``dict`` of those, so the recursive
    default handles the whole tree with no manual field-by-field walk."""
    return asdict(report)


_REPORT_FIELDS = frozenset(("slug", "gates"))
_GATE_RESULT_FIELDS = frozenset(("status", "findings", "artifacts", "error"))
_FINDING_FIELDS = frozenset(("slide_id", "message"))
_GATE_STATUSES = frozenset(("ok", "error"))


def _finding_from_dict(gate_id: str, index: int, entry: object) -> Finding:
    malformed = f"gate {gate_id!r} finding #{index} is malformed"
    if not isinstance(entry, dict):
        raise errors.HeraldError(f"{malformed}: entry is not a JSON object")
    unknown = sorted(set(entry) - _FINDING_FIELDS)
    if unknown:
        raise errors.HeraldError(f"{malformed}: unknown field(s) {', '.join(map(repr, unknown))}")
    missing = sorted(_FINDING_FIELDS - set(entry))
    if missing:
        raise errors.HeraldError(f"{malformed}: missing field(s) {', '.join(map(repr, missing))}")
    slide_id = entry["slide_id"]
    message = entry["message"]
    if not isinstance(slide_id, str) or not isinstance(message, str):
        raise errors.HeraldError(f"{malformed}: 'slide_id' and 'message' must both be strings")
    return Finding(slide_id=slide_id, message=message)


def _gate_result_from_dict(gate_id: str, entry: object) -> GateResult:
    malformed = f"gate {gate_id!r} entry is malformed"
    if not isinstance(entry, dict):
        raise errors.HeraldError(f"{malformed}: entry is not a JSON object")
    unknown = sorted(set(entry) - _GATE_RESULT_FIELDS)
    if unknown:
        raise errors.HeraldError(f"{malformed}: unknown field(s) {', '.join(map(repr, unknown))}")
    missing = sorted(_GATE_RESULT_FIELDS - set(entry))
    if missing:
        raise errors.HeraldError(f"{malformed}: missing field(s) {', '.join(map(repr, missing))}")
    status = entry["status"]
    if status not in _GATE_STATUSES:
        raise errors.HeraldError(f"{malformed}: 'status' must be one of {sorted(_GATE_STATUSES)}, got {status!r}")
    findings = entry["findings"]
    if not isinstance(findings, list):
        raise errors.HeraldError(f"{malformed}: 'findings' must be a list")
    artifacts = entry["artifacts"]
    if not isinstance(artifacts, list) or not all(isinstance(a, str) for a in artifacts):
        raise errors.HeraldError(f"{malformed}: 'artifacts' must be a list of strings")
    error = entry["error"]
    if error is not None and not isinstance(error, str):
        raise errors.HeraldError(f"{malformed}: 'error' must be a string or null")
    if (status == "error") != (error is not None):
        raise errors.HeraldError(
            f"{malformed}: 'status'=={status!r} requires 'error' to be "
            f"{'non-null' if status == 'error' else 'null'}, got {error!r}"
        )
    return GateResult(
        status=status,
        findings=[_finding_from_dict(gate_id, i, item) for i, item in enumerate(findings)],
        artifacts=list(artifacts),
        error=error,
    )


def parse_report(data: object) -> DeckQaReport:
    """The strict inverse of ``to_dict`` (AD-6, mirroring ``state.py``):
    raises ``errors.HeraldError`` naming the problem on any missing or
    unrecognized top-level/gate-level/finding-level field, a wrong field
    type, or a ``status`` value other than ``"ok"``/``"error"`` -- a typoed
    field or a corrupt hand-edit is never silently dropped or coerced."""
    if not isinstance(data, dict):
        raise errors.HeraldError("deck QA report is malformed: top level is not a JSON object")
    unknown = sorted(set(data) - _REPORT_FIELDS)
    if unknown:
        raise errors.HeraldError(f"deck QA report is malformed: unknown field(s) {', '.join(map(repr, unknown))}")
    missing = sorted(_REPORT_FIELDS - set(data))
    if missing:
        raise errors.HeraldError(f"deck QA report is malformed: missing field(s) {', '.join(map(repr, missing))}")
    slug = data["slug"]
    if not isinstance(slug, str):
        raise errors.HeraldError("deck QA report is malformed: 'slug' must be a string")
    gates = data["gates"]
    if not isinstance(gates, dict) or not all(isinstance(k, str) for k in gates):
        raise errors.HeraldError("deck QA report is malformed: 'gates' must be an object with string keys")
    return DeckQaReport(
        slug=slug,
        gates={gate_id: _gate_result_from_dict(gate_id, entry) for gate_id, entry in gates.items()},
    )
