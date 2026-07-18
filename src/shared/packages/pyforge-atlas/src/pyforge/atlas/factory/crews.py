"""The three Karpathy-wiki agno crews — compile / lint / Q&A (Story H2, FR-22(b), AD-13/AD-22).

The AI Software Factory maintains its wiki with agent labor (§ 7.3). H2 lands the three crews
that do that work, each mapped to its § 2.2 persona(s):

* :class:`CompileCrew`  (Compiler + Linker) — ``wiki/raw/`` markdown → ``wiki/compiled/``.
* :class:`LintCrew`     (Linter/QA)         — validates ``wiki/compiled/``, reports violations.
* :class:`QACrew`       (Oracle + Ingester) — answers a question GROUNDED in compiled content.

**Offline-first, LLM-synthesis injectable (the D3/F3/G3 pattern).** Every crew's core transform
is DETERMINISTIC and runs with no network and no model — so the H2 gate exercises the real
raw→compiled→answer flow on a fixture wiki. The LLM/`agno`-Agent enrichment + synthesis is an
INJECTABLE seam that defaults to the offline deterministic path; standing up a live model backend
(via :func:`pyforge.atlas.nl.backend.resolve_backend` — repo model-backend routing, never a
hardcoded endpoint) and running the crews through an actual `agno` Agent is the attended
deferral (DW-H2). Nothing here imports a live model or calls the network.

**AD-13/AD-22 — republication never launders freshness (the load-bearing H2 invariant).** A raw
doc may carry a :class:`~pyforge.atlas.datasets.refresh.StalenessMarker` (the same
``.staleness.json`` sidecar shape the datasets write). :class:`CompileCrew` PROPAGATES that marker
into the compiled page's frontmatter AND stamps a visible stale banner in the body — a stale
source can never produce a compiled page that reads as fresh. :class:`LintCrew` enforces the
banner's presence, so a laundered page is a reported violation.

**AD-22 write-boundary.** The crews read atlas datasets / the raw wiki and write ONLY the wiki
tree (through :class:`~pyforge.atlas.factory.wiki.WikiLayout`, whose ``stage_path`` refuses any
escape). No crew writes an atlas dataset.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import yaml

from .wiki import WikiLayout

# ---------------------------------------------------------------------------
# Frontmatter (the compiled-page metadata carrier) — parse + serialize once here.
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)


class _StrictSafeLoader(yaml.SafeLoader):
    """SafeLoader that additionally rejects YAML aliases (billion-laughs / entity-expansion
    resource exhaustion) and duplicate mapping keys — raw wiki docs can be UNTRUSTED (the
    Ingester reads incoming payloads), so hardening the frontmatter parser is warranted
    (Gemini #100)."""

    def compose_node(self, parent, index):  # type: ignore[override]
        if self.check_event(yaml.AliasEvent):
            raise yaml.YAMLError("YAML aliases are not allowed in wiki frontmatter")
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):  # type: ignore[override]
        seen: set = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.YAMLError(f"duplicate key {key!r} in wiki frontmatter")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)

#: The visible stale banner stamped into a compiled body when the source is stale. LintCrew
#: checks for this exact prefix so a stale page that drops the banner is a reported violation.
STALE_BANNER_PREFIX = "> ⚠️ STALE"


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split ``text`` into ``(frontmatter_dict, body)``. A doc with no ``---`` block yields an
    empty dict + the whole text. Malformed YAML in the block raises ``yaml.YAMLError`` (a broken
    page must fail loudly, not silently lose its metadata)."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.load(m.group(1), Loader=_StrictSafeLoader) or {}
    if not isinstance(meta, dict):
        raise ValueError(f"frontmatter must be a mapping, got {type(meta).__name__}")
    return meta, m.group(2)


def serialize_frontmatter(meta: Mapping[str, Any], body: str) -> str:
    """Render ``meta`` + ``body`` back to a frontmatter document. Keys are sorted so the output
    is byte-stable across two compiles of the same input (AD-21 determinism, mirroring the
    publish emitter)."""
    if not meta:
        return body
    front = yaml.safe_dump(dict(meta), sort_keys=True, allow_unicode=True).strip()
    return f"---\n{front}\n---\n{body}"


# ---------------------------------------------------------------------------
# Staleness (AD-13) — read the source marker, project it onto the compiled page.
# ---------------------------------------------------------------------------

#: sidecar suffix for a raw doc's staleness marker. NOTE the layout difference from the refresh
#: datasets: those write ``<store-dir>/.staleness.json`` INSIDE a store *directory*
#: (``refresh.py``), whereas a raw wiki doc is a *file*, so its marker is a SIBLING
#: ``<name>.md.staleness.json`` (the ``p.name + STALENESS_FILENAME`` shape, applied to a file).
#: The marker DICT shape (``{stale, reason, marked_at, ...}``) is identical, so a dataset-authored
#: marker is understood field-for-field once it is placed beside the raw file — but the on-disk
#: path is not interchangeable between a directory store and a file, so do not assume a dataset's
#: sidecar is read in place; the Ingester (deferred) is what lands it next to the raw doc.
STALENESS_SUFFIX = ".staleness.json"


def _read_staleness(raw_doc: Path) -> dict[str, Any] | None:
    """Return the raw doc's SIDECAR staleness marker dict if the sidecar exists and marks it
    stale, else ``None``. A malformed sidecar is treated as an UNKNOWN-but-present staleness
    (stale=True, reason names the parse failure) — degrade toward stale, never silently toward
    fresh (AD-13)."""
    sidecar = raw_doc.with_name(raw_doc.name + STALENESS_SUFFIX)
    if not sidecar.exists():
        return None
    try:
        marker = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"stale": True, "reason": f"unreadable staleness sidecar {sidecar.name}"}
    if not isinstance(marker, dict) or not marker.get("stale"):
        return None
    return marker


def _inline_staleness(meta: Mapping[str, Any]) -> dict[str, Any] | None:
    """Staleness declared in the raw doc's OWN frontmatter (``stale: true`` [+ ``stale_reason`` /
    ``stale_marked_at`` / ``marked_at``]). A raw doc that calls itself stale is unambiguously a
    stale source — this is the second staleness carrier, so it can never be laundered away by the
    compile step (MUST-FIX: previously the raw frontmatter was rebuilt from scratch and this was
    silently dropped)."""
    if not meta.get("stale"):
        return None
    marker: dict[str, Any] = {
        "stale": True,
        "reason": str(meta.get("stale_reason", "source frontmatter marked stale")),
    }
    marked = meta.get("stale_marked_at", meta.get("marked_at"))
    if marked is not None:
        marker["marked_at"] = marked
    return marker


def _resolve_staleness(meta: Mapping[str, Any], raw_doc: Path) -> dict[str, Any] | None:
    """The source's effective staleness = the UNION of both carriers (inline frontmatter OR the
    ``.staleness.json`` sidecar). Stale if EITHER says stale (AD-13: never degrade toward fresh);
    when both are stale the sidecar's ``marked_at`` wins and the reasons combine."""
    inline = _inline_staleness(meta)
    sidecar = _read_staleness(raw_doc)
    if inline is None:
        return sidecar
    if sidecar is None:
        return inline
    reasons = [r for r in (sidecar.get("reason"), inline.get("reason")) if r]
    merged: dict[str, Any] = {"stale": True, "reason": "; ".join(dict.fromkeys(reasons))}
    marked = sidecar.get("marked_at", inline.get("marked_at"))
    if marked is not None:
        merged["marked_at"] = marked
    return merged


# ---------------------------------------------------------------------------
# Compile crew (Compiler + Linker).
# ---------------------------------------------------------------------------

#: An enricher augments a compiled body (e.g. an `agno` Agent summarizing / linking). It takes
#: ``(title, body)`` and returns a new body. The default is the offline identity (no model).
Enricher = Callable[[str, str], str]


def _identity_enricher(_title: str, body: str) -> str:
    return body


@dataclass
class CompileResult:
    compiled: list[str] = field(default_factory=list)  # compiled doc names, sorted
    stale_forwarded: list[str] = field(default_factory=list)  # names whose staleness propagated
    failed: list[tuple[str, str]] = field(default_factory=list)  # (name, reason) skipped docs

    @property
    def count(self) -> int:
        return len(self.compiled)


class CompileCrew:
    """Transforms every ``wiki/raw/*.md`` into a structured ``wiki/compiled/*.md`` page.

    Deterministic core: parse the raw doc, ensure a ``title`` (from frontmatter or the first ``#``
    heading or the stem), carry the ``source`` reference, PROPAGATE any source staleness marker
    into the compiled frontmatter + a visible body banner (AD-13/AD-22), then run the injected
    ``enricher`` (default offline identity) over the body. Output frontmatter is byte-stable.
    """

    def __init__(self, *, enricher: Enricher = _identity_enricher) -> None:
        self._enricher = enricher

    def run(self, layout: WikiLayout) -> CompileResult:
        raw_dir = layout.stage_dir("raw")
        result = CompileResult()
        for raw_doc in sorted(raw_dir.glob("*.md")):
            name = raw_doc.name
            try:
                meta, body = parse_frontmatter(raw_doc.read_text(encoding="utf-8"))
            except (yaml.YAMLError, ValueError) as exc:
                # A malformed raw doc must not abort the whole compile mid-loop (which would leave
                # compiled/ half-rewritten). Skip it, record why, and keep compiling the rest —
                # the failure is surfaced in result.failed, never silently swallowed.
                result.failed.append((name, f"{type(exc).__name__}: {exc}"))
                continue
            title = self._title_of(meta, body, raw_doc.stem)

            compiled_meta: dict[str, Any] = {"title": title, "source": f"raw/{name}"}
            # Effective staleness = inline frontmatter OR sidecar (either carrier — never
            # laundered). MUST-FIX: the raw doc's own `stale:` frontmatter is honored, not just
            # the sidecar.
            marker = _resolve_staleness(meta, raw_doc)
            if marker is not None:
                # AD-13/AD-22: forward the source's staleness — the compiled page cannot read as
                # fresh. Both machine-readable (frontmatter) AND human-visible (body banner).
                compiled_meta["stale"] = True
                compiled_meta["stale_reason"] = str(marker.get("reason", "source marked stale"))
                if "marked_at" in marker:
                    compiled_meta["stale_marked_at"] = marker["marked_at"]
                body = self._prepend_banner(body, compiled_meta["stale_reason"])
                result.stale_forwarded.append(name)

            enriched = self._enricher(title, body)
            out_text = serialize_frontmatter(compiled_meta, enriched)
            layout.stage_path("compiled", name).write_text(out_text, encoding="utf-8")
            result.compiled.append(name)
        result.compiled.sort()
        result.stale_forwarded.sort()
        return result

    @staticmethod
    def _title_of(meta: Mapping[str, Any], body: str, stem: str) -> str:
        if meta.get("title"):
            return str(meta["title"])
        for line in body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return stem

    @staticmethod
    def _prepend_banner(body: str, reason: str) -> str:
        banner = f"{STALE_BANNER_PREFIX}: {reason}\n\n"
        return banner + body.lstrip("\n")


# ---------------------------------------------------------------------------
# Lint crew (Linter/QA).
# ---------------------------------------------------------------------------

_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


@dataclass(frozen=True)
class LintViolation:
    doc: str
    rule: str
    detail: str


@dataclass
class LintReport:
    violations: list[LintViolation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations

    def by_rule(self, rule: str) -> list[LintViolation]:
        return [v for v in self.violations if v.rule == rule]


class LintCrew:
    """Validates ``wiki/compiled/`` and reports violations (never raises on a bad page — it
    REPORTS, so an operator sees every problem at once).

    Rules: ``missing-frontmatter``, ``missing-title``, ``empty-body``, ``broken-link`` (an
    internal ``*.md`` link with no target in ``compiled/``), and ``laundered-staleness`` (a page
    whose frontmatter says ``stale`` but whose body dropped the :data:`STALE_BANNER_PREFIX`
    banner — the AD-13/AD-22 guard that republication never launders freshness)."""

    def run(self, layout: WikiLayout) -> LintReport:
        compiled_dir = layout.stage_dir("compiled")
        compiled_root = compiled_dir.resolve()
        report = LintReport()
        for doc in sorted(compiled_dir.rglob("*.md")):
            name = str(doc.relative_to(compiled_dir))
            try:
                meta, body = parse_frontmatter(doc.read_text(encoding="utf-8"))
            except (yaml.YAMLError, ValueError) as exc:
                # Lint REPORTS on a bad page, never raises (docstring contract) — a single
                # malformed page must not DoS the whole pass and hide other violations.
                report.violations.append(
                    LintViolation(name, "malformed-frontmatter", f"{type(exc).__name__}: {exc}")
                )
                continue
            if not meta:
                report.violations.append(
                    LintViolation(name, "missing-frontmatter", "no YAML frontmatter block")
                )
            elif not meta.get("title"):
                report.violations.append(
                    LintViolation(name, "missing-title", "frontmatter has no 'title'")
                )
            if not body.strip():
                report.violations.append(LintViolation(name, "empty-body", "body is empty"))
            if meta.get("stale") and STALE_BANNER_PREFIX not in body:
                report.violations.append(
                    LintViolation(
                        name,
                        "laundered-staleness",
                        "frontmatter marks the page stale but the body dropped the stale banner "
                        "(AD-13/AD-22: republication must not launder freshness)",
                    )
                )
            for target in _LINK_RE.findall(body):
                # Only internal, in-tree *.md links are checkable; skip URLs, anchors, mailto.
                if "://" in target or target.startswith(("#", "mailto:")):
                    continue
                path_part = target.split("#")[0].strip()
                if not path_part.endswith(".md"):
                    continue
                # Resolve RELATIVE TO THE DOC'S OWN DIRECTORY against the real tree (not a
                # leaf-name membership test — that both false-negatives a wrong subdir and
                # false-positives a real subdir page). A link that escapes compiled/ is itself a
                # violation.
                resolved = (doc.parent / path_part).resolve()
                try:
                    resolved.relative_to(compiled_root)
                except ValueError:
                    report.violations.append(
                        LintViolation(name, "broken-link", f"link target {target!r} escapes compiled/")
                    )
                    continue
                if not resolved.is_file():
                    report.violations.append(
                        LintViolation(name, "broken-link", f"link target {target!r} not in compiled/")
                    )
        return report


# ---------------------------------------------------------------------------
# Q&A crew (Oracle + Ingester).
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[A-Za-z0-9]+")


@dataclass(frozen=True)
class Grounding:
    doc: str
    snippet: str
    score: float


@dataclass
class QAAnswer:
    question: str
    answer: str
    grounding: list[Grounding] = field(default_factory=list)

    @property
    def grounded(self) -> bool:
        """True iff the answer is backed by at least one compiled snippet (never an ungrounded
        hallucination — the Oracle answers FROM compiled content)."""
        return bool(self.grounding)


#: A retriever ranks compiled docs for a question. It takes ``(question, [(name, body), ...])``
#: and returns ranked ``Grounding``. The default is deterministic keyword-overlap (offline, no
#: vss); the F3 :class:`~pyforge.atlas.rag.store.DuckdbVssRagStore` is the production retriever an
#: operator injects (its similarity_search wrapped to this signature) — DW-H2.
Retriever = Callable[[str, Sequence[tuple[str, str]]], list["Grounding"]]

#: A synthesizer turns the question + grounding into an answer string. The default is offline
#: EXTRACTIVE (returns the top grounding snippet, clearly not a generative claim); an `agno` Agent
#: over a resolved model backend is the injectable+deferred generative path (DW-H2).
Synthesizer = Callable[[str, Sequence["Grounding"]], str]


def keyword_retriever(
    question: str, docs: Sequence[tuple[str, str]], *, k: int = 3
) -> list[Grounding]:
    """Deterministic keyword-overlap retrieval (offline; no vss needed). Scores each doc by the
    number of DISTINCT question terms it contains, drops zero-overlap docs, and returns the top
    ``k`` (ties broken by doc name for determinism). The snippet is the first line mentioning a
    query term (or the doc's opening line)."""
    q_terms = {t.lower() for t in _WORD_RE.findall(question)}
    scored: list[Grounding] = []
    for name, body in docs:
        d_terms = {t.lower() for t in _WORD_RE.findall(body)}
        overlap = q_terms & d_terms
        if not overlap:
            continue
        scored.append(Grounding(doc=name, snippet=_snippet(body, overlap), score=float(len(overlap))))
    scored.sort(key=lambda g: (-g.score, g.doc))
    return scored[:k]


def _snippet(body: str, terms: set[str], *, width: int = 200) -> str:
    for line in body.splitlines():
        low = line.lower()
        if any(t in low for t in terms):
            return line.strip()[:width]
    stripped = body.strip()
    return stripped[:width]


def _extractive_synthesizer(question: str, grounding: Sequence[Grounding]) -> str:
    if not grounding:
        return (
            f"No compiled content answers {question!r}. (The Q&A crew answers only from the "
            "compiled wiki — no ungrounded answer is produced.)"
        )
    top = grounding[0]
    return f"From {top.doc}: {top.snippet}"


class QACrew:
    """Answers a question GROUNDED in ``wiki/compiled/`` content.

    Retrieval + synthesis are both injectable; the defaults are offline (keyword retrieval +
    extractive synthesis) so the crew answers from the fixture wiki with no model. An answer is
    only ever built from retrieved compiled snippets — :attr:`QAAnswer.grounded` is the contract
    that the Oracle never hallucinates past the compiled content."""

    def __init__(
        self,
        *,
        retriever: Retriever | None = None,
        synthesizer: Synthesizer = _extractive_synthesizer,
        k: int = 3,
    ) -> None:
        self._retriever = retriever or (lambda q, docs: keyword_retriever(q, docs, k=k))
        self._synthesizer = synthesizer
        self._k = k

    def run(self, layout: WikiLayout, question: str) -> QAAnswer:
        compiled_dir = layout.stage_dir("compiled")
        docs: list[tuple[str, str]] = []
        for doc in sorted(compiled_dir.rglob("*.md")):
            try:
                _meta, body = parse_frontmatter(doc.read_text(encoding="utf-8"))
            except (yaml.YAMLError, ValueError):
                # A malformed page can't be grounded on — skip it rather than crash the whole
                # answer (an operator's question must still be answered from the good pages).
                continue
            docs.append((str(doc.relative_to(compiled_dir)), body))
        grounding = list(self._retriever(question, docs))
        answer = self._synthesizer(question, grounding)
        return QAAnswer(question=question, answer=answer, grounding=grounding)
