"""Steward's ``catalog`` duty — the estate BMAD catalog: config names backends
and sources (Story 60.1, spec-self-hosted-bmad-marketplace CAP-1 /
spec-pyforge-steward CAP-117).

Git is the edit store: ``src/shared/packages/pyforge-steward/catalog/`` is
tracked in this repo and is where listings are edited. ``catalog.yaml`` there
is the declaration — every ship backend and every source of
``backends-and-sources.md`` appears by name with its v1 ``state``
(``on | off | available``) and the ``plugin`` that binds it. A new backend or
source is a new declared row plus a plugin implementing
:class:`CatalogSourcePlugin` / :class:`ShipBackendPlugin`, registered on the
engine's :class:`SourceRegistry` / :class:`BackendRegistry` — never an engine
rewrite (the ledger-query registry idiom: ABC + in-module registry, duplicate
name → ``ValueError``, engine self-registers its defaults).

The engine reads the declared sources and renders two GENERATED manifests
beside the config (never hand-edited): ``.claude-plugin/marketplace.json``
(the Claude Code marketplace manifest, also what the BMAD installer's
``--custom-source`` discovery mode reads) and ``.agents/plugins/marketplace.json``
(Codex). Provenance rides in *their* format — Claude's plugin entry already
uses ``source`` for "where to fetch", so the producing source and trust tier
are carried as ``tags: ["source:<name>", "trust:<tier>"]``.

Backends here are declarations with the shared snapshot interface
(``snapshot_target``); the conda publish itself is Story 60.3. Nothing here
edits ``.claude/settings.json`` or mints a GitHub repository — both are
operator-confirm moments; ``steward catalog pointers`` prints the forms that
work today (``--custom-source`` / ``extraKnownMarketplaces`` ``directory``)
and names the ``github`` forms as waiting on ``edit_store.dedicated_repo``.

Verbs: ``steward catalog check|list|render [--check]|pointers [--json]``.
``CatalogDuty`` never calls ``sys.exit`` (AD-8) — it returns a
``DutyResult`` and ``cli.main`` projects it.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .bootstrap import repo_root
from .frames import preflight_frames
from .interfaces import DutyResult
from .suite import INSTALL_CLASS_MODULE, SUITE_PACKAGES, read_recipe_version

CATALOG_RELATIVE = Path("src/shared/packages/pyforge-steward/catalog")
CONFIG_FILENAME = "catalog.yaml"
CLAUDE_MANIFEST_RELATIVE = Path(".claude-plugin/marketplace.json")
CODEX_MANIFEST_RELATIVE = Path(".agents/plugins/marketplace.json")
DEFAULT_ESTATE_REGISTRY = "registry/estate.yaml"

STATES: tuple[str, ...] = ("on", "off", "available")
STATE_ON, STATE_OFF, STATE_AVAILABLE = STATES
TRUST_TIERS: tuple[str, ...] = ("unverified", "community-reviewed", "bmad-certified")
TIER_UNVERIFIED, TIER_COMMUNITY_REVIEWED, TIER_BMAD_CERTIFIED = TRUST_TIERS
KIND_MODULE = "module"
KIND_FRAME = "frame"

VERBS: tuple[str, ...] = ("check", "list", "render", "pointers")

UPSTREAM_REGISTRY_SCHEMA_URL = (
    "https://github.com/bmad-code-org/bmad-plugins-marketplace/blob/main/registry/registry-schema.yaml"
)


# ── config (`catalog/catalog.yaml`) ──────────────────────────────────────────


class CatalogConfigError(ValueError):
    """A missing or malformed catalog document (``catalog.yaml`` or a source's
    own file, e.g. ``registry/estate.yaml``)."""


@dataclass(frozen=True)
class BackendDecl:
    """One declared ship backend: ``backends.<name>{plugin, state, …}``.
    ``plugin`` is ``None`` for an empty slot (declared, unbound; never ``on``)."""

    name: str
    plugin: str | None
    state: str
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceDecl:
    """One declared source: ``sources.<name>{plugin, state, …}``.
    ``plugin`` is ``None`` for an empty slot (declared, unbound; never ``on``)."""

    name: str
    plugin: str | None
    state: str
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EditStore:
    """Where listings are edited. ``dedicated_repo`` is ``None`` until an
    operator confirms minting a GitHub catalog repo."""

    kind: str
    repo: str
    path: str
    dedicated_repo: str | None = None


@dataclass(frozen=True)
class CatalogConfig:
    """The operator-declared catalog: identity, edit store, backends, sources."""

    name: str
    owner: str
    edit_store: EditStore
    backends: tuple[BackendDecl, ...]
    sources: tuple[SourceDecl, ...]
    display_name: str = ""
    description: str = ""


def default_catalog_dir(root: Path | None = None) -> Path:
    """``src/shared/packages/pyforge-steward/catalog`` at the repo root."""
    return (root if root is not None else repo_root()) / CATALOG_RELATIVE


def _load_yaml_mapping(document_path: Path, *, what: str) -> dict[str, Any]:
    """``yaml.safe_load`` a file that must be a mapping — the four named load
    failures (``sync.load_config`` precedent): missing, malformed, unreadable,
    not-a-mapping."""
    if not document_path.is_file():
        raise CatalogConfigError(f"{document_path}: {what} not found")
    try:
        with document_path.open("r", encoding="utf-8") as f:
            document = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise CatalogConfigError(f"{document_path}: malformed YAML: {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise CatalogConfigError(f"{document_path}: unreadable: {exc}") from exc
    if document is None:
        document = {}
    if not isinstance(document, dict):
        raise CatalogConfigError(
            f"{document_path}: top-level document must be a mapping, got {type(document).__name__}"
        )
    return document


def _require_str(document_path: Path, mapping: dict[str, Any], key: str, where: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CatalogConfigError(f"{document_path}: '{where}.{key}' is required and must be a non-empty string")
    return value.strip()


def _normalize_state(document_path: Path, raw: object, where: str) -> str:
    # Bare `on`/`off` are YAML 1.1 booleans; accept them as the words they were.
    if isinstance(raw, bool):
        raw = STATE_ON if raw else STATE_OFF
    if not isinstance(raw, str) or raw.strip() not in STATES:
        raise CatalogConfigError(f"{document_path}: '{where}.state' = {raw!r} is not one of {STATES!r}")
    return raw.strip()


def _parse_decls(document_path: Path, section: object, section_name: str, factory: type) -> tuple[Any, ...]:
    if section is None:
        section = {}
    if not isinstance(section, dict):
        raise CatalogConfigError(f"{document_path}: {section_name!r} section must be a mapping")
    decls = []
    for name, body in section.items():
        # A bare `on:` / `yes:` key parses to a YAML boolean; it is not a name.
        if not isinstance(name, str) or not name.strip():
            raise CatalogConfigError(
                f"{document_path}: {section_name!r} key {name!r} must be a non-empty string "
                "(quote it if YAML reads it as a boolean)"
            )
        where = f"{section_name}.{name}"
        if not isinstance(body, dict):
            raise CatalogConfigError(f"{document_path}: '{where}' must be a mapping")
        state = _normalize_state(document_path, body.get("state"), where)
        plugin = body.get("plugin")
        if plugin is None:
            # An empty slot: declared, not yet bound. Only legal while it is off.
            if state == STATE_ON:
                raise CatalogConfigError(
                    f"{document_path}: '{where}' is 'on' but names no 'plugin' (the plugin that binds it)"
                )
        elif not isinstance(plugin, str) or not plugin.strip():
            raise CatalogConfigError(
                f"{document_path}: '{where}.plugin' must be null (an empty slot) or a non-empty string"
            )
        else:
            plugin = plugin.strip()
        options = {k: v for k, v in body.items() if k not in ("plugin", "state")}
        decls.append(factory(name=name.strip(), plugin=plugin, state=state, options=options))
    return tuple(decls)


_TOP_LEVEL_KEYS: frozenset[str] = frozenset({"catalog", "backends", "sources"})


def load_config(path: str | Path) -> CatalogConfig:
    """Load ``catalog.yaml``-shaped YAML from ``path`` (``yaml.safe_load`` only)."""
    document_path = Path(path)
    document = _load_yaml_mapping(document_path, what="catalog config")

    unknown = sorted(str(k) for k in document if k not in _TOP_LEVEL_KEYS)
    if unknown:
        raise CatalogConfigError(
            f"{document_path}: unknown top-level key(s) {unknown!r}; only "
            f"{sorted(_TOP_LEVEL_KEYS)!r} are recognized (a misspelled section would "
            "otherwise load as zero backends/sources)"
        )

    catalog = document.get("catalog")
    if not isinstance(catalog, dict):
        raise CatalogConfigError(f"{document_path}: 'catalog' section missing or not a mapping")
    name = _require_str(document_path, catalog, "name", "catalog")
    owner = _require_str(document_path, catalog, "owner", "catalog")

    store = catalog.get("edit_store")
    if not isinstance(store, dict):
        raise CatalogConfigError(f"{document_path}: 'catalog.edit_store' section missing or not a mapping")
    kind = _require_str(document_path, store, "kind", "catalog.edit_store")
    if kind != "git":
        raise CatalogConfigError(f"{document_path}: 'catalog.edit_store.kind' = {kind!r}; git is the edit store")
    dedicated = store.get("dedicated_repo")
    if dedicated is not None and (not isinstance(dedicated, str) or _github_owner_repo(dedicated) != dedicated.strip()):
        raise CatalogConfigError(
            f"{document_path}: 'catalog.edit_store.dedicated_repo' must be null or an "
            f"owner/repo string, got {dedicated!r}"
        )
    edit_store = EditStore(
        kind=kind,
        repo=_require_str(document_path, store, "repo", "catalog.edit_store"),
        path=_require_str(document_path, store, "path", "catalog.edit_store"),
        dedicated_repo=dedicated.strip() if isinstance(dedicated, str) else None,
    )

    backends = _parse_decls(document_path, document.get("backends"), "backends", BackendDecl)
    sources = _parse_decls(document_path, document.get("sources"), "sources", SourceDecl)

    display_name = catalog.get("display_name")
    description = catalog.get("description")
    return CatalogConfig(
        name=name,
        owner=owner,
        edit_store=edit_store,
        backends=backends,
        sources=sources,
        display_name=(display_name.strip() if isinstance(display_name, str) and display_name.strip() else name),
        description=description.strip() if isinstance(description, str) else "",
    )


# ── listings ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Listing:
    """One row on the list. A listing names exactly one ``source``."""

    name: str
    kind: str
    source: str
    trust_tier: str
    description: str = ""
    repository: str | None = None
    version: str | None = None
    code: str | None = None
    install_hint: str | None = None
    link: str | None = None
    codex_source: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "source": self.source,
            "trust_tier": self.trust_tier,
            "description": self.description,
            "repository": self.repository,
            "version": self.version,
            "code": self.code,
            "install_hint": self.install_hint,
            "link": self.link,
            "codex_source": self.codex_source,
        }


@dataclass(frozen=True)
class SourceContext:
    """What a source plugin gets to produce its listings from."""

    repo_root: Path
    catalog_dir: Path
    config: CatalogConfig
    decl: SourceDecl


# ── plugin interfaces & registries ───────────────────────────────────────────


class CatalogSourcePlugin(ABC):
    """Abstract interface for a source (what may appear on the list)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier a ``sources.<name>.plugin`` row binds to."""

    @abstractmethod
    def listings(self, ctx: SourceContext) -> list[Listing]:
        """Produce this source's listings. Raise ``CatalogConfigError`` for a
        malformed source file; the engine reports it as a ``config-*`` finding."""


class ShipBackendPlugin(ABC):
    """Abstract interface for a ship backend — the shared snapshot interface.
    Story 60.3 adds ``ship``; a backend here never claims to ship."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier a ``backends.<name>.plugin`` row binds to."""

    @abstractmethod
    def snapshot_target(self, decl: BackendDecl) -> str:
        """Where this backend would put the catalog snapshot, from the declaration."""


class _Registry:
    kind = "plugin"

    def __init__(self) -> None:
        self._plugins: dict[str, Any] = {}

    def register(self, plugin: Any) -> None:
        if plugin.name in self._plugins:
            raise ValueError(f"{self.kind} {plugin.name!r} is already registered")
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> Any:
        if name not in self._plugins:
            raise KeyError(f"Unknown {self.kind}: {name!r}. Registered: {self.names()}")
        return self._plugins[name]

    def names(self) -> list[str]:
        return sorted(self._plugins)

    def __contains__(self, name: object) -> bool:
        return name in self._plugins


class SourceRegistry(_Registry):
    """Registry for source plugins; the engine binds each declared source through it."""

    kind = "source"


class BackendRegistry(_Registry):
    """Registry for ship backends; the engine binds each declared backend through it."""

    kind = "backend"


# ── default sources ──────────────────────────────────────────────────────────


def _version_text(raw: object) -> str | None:
    """``suite.read_recipe_version``'s rule: a ``str`` as-is, a non-bool ``int``
    as ``str(int)``, anything else (an unquoted YAML float like ``1.10`` →
    ``1.1``, a bool, a list) → ``None``."""
    if isinstance(raw, str):
        return raw.strip() or None
    if isinstance(raw, int) and not isinstance(raw, bool):
        return str(raw)
    return None


class EstateListingsSource(CatalogSourcePlugin):
    """``registry/estate.yaml`` — YAML we authored and steward reviewed, in the
    upstream registry file format (``modules: [{name, …, trust_tier}]``).

    Anchor: the declared ``path`` is **catalog-dir-relative** (it names a file
    inside the edit store; default ``registry/estate.yaml``). A file-level
    ``source:``, when present, must equal this plugin's name (absent means
    this plugin); a per-row ``source:`` defaults to it and, when it differs,
    the engine reports ``listing-source-mismatch``. ``trust_tier`` must be one
    of ``TRUST_TIERS`` — a typo'd tier never reaches a manifest tag.
    """

    @property
    def name(self) -> str:
        return "estate-listings"

    def listings(self, ctx: SourceContext) -> list[Listing]:
        rel = ctx.decl.options.get("path") or DEFAULT_ESTATE_REGISTRY
        path = ctx.catalog_dir / str(rel)
        document = _load_yaml_mapping(path, what="estate listings")
        file_source = document.get("source")
        if file_source is not None and file_source != self.name:
            raise CatalogConfigError(
                f"{path}: 'source' is {file_source!r}; this file feeds exactly one "
                f"declared source and must say {self.name!r}"
            )
        modules = document.get("modules")
        if modules is None:
            modules = []
        if not isinstance(modules, list):
            raise CatalogConfigError(f"{path}: 'modules' must be a list")
        rows: list[Listing] = []
        for index, row in enumerate(modules):
            if not isinstance(row, dict):
                raise CatalogConfigError(f"{path}: modules[{index}] must be a mapping")
            name = row.get("name")
            if not isinstance(name, str) or not name.strip():
                raise CatalogConfigError(f"{path}: modules[{index}].name is required and must be a non-empty string")
            tier = row.get("trust_tier")
            if tier is None:
                tier = TIER_UNVERIFIED
            if tier not in TRUST_TIERS:
                raise CatalogConfigError(
                    f"{path}: modules[{index}].trust_tier = {tier!r} is not one of {TRUST_TIERS!r}"
                )
            row_source = row.get("source", self.name)
            repository = row.get("repository")
            rows.append(
                Listing(
                    name=name.strip(),
                    kind=KIND_MODULE,
                    source=str(row_source) if row_source is not None else "",
                    trust_tier=tier,
                    description=str(row.get("description") or ""),
                    repository=str(repository) if repository else None,
                    version=_version_text(row.get("version")),
                    code=str(row["code"]) if row.get("code") else None,
                    install_hint=str(row["install_hint"]) if row.get("install_hint") else None,
                    link=str(row.get("homepage") or repository or "") or None,
                    codex_source=str(row["codex_source"]) if row.get("codex_source") else None,
                )
            )
        return rows


def _read_recipe_about(repo: Path, package: str) -> dict[str, str]:
    """Fail-open ``recipes/<package>/recipe.yaml`` ``about`` strings (mirrors
    ``suite.read_recipe_version``: never raises)."""
    try:
        data = yaml.safe_load((repo / "recipes" / package / "recipe.yaml").read_text(encoding="utf-8"))
        about = data["about"]
        return {k: v for k, v in about.items() if isinstance(v, str)}
    except OSError, ValueError, yaml.YAMLError, KeyError, TypeError, AttributeError:
        return {}


class WieldedSuiteSource(CatalogSourcePlugin):
    """Official modules we already install — the ``install_class == "module"``
    rows of ``suite.SUITE_PACKAGES`` (never a second roster), Certified because
    they are already in the wielded suite (ruling 5)."""

    @property
    def name(self) -> str:
        return "wielded-suite"

    def listings(self, ctx: SourceContext) -> list[Listing]:
        rows: list[Listing] = []
        for pkg in SUITE_PACKAGES:
            if pkg.install_class != INSTALL_CLASS_MODULE:
                continue
            about = _read_recipe_about(ctx.repo_root, pkg.name)
            repository = f"https://github.com/{pkg.github_repo}" if pkg.github_repo else None
            code = pkg.module_code or (pkg.wire_bmad_config_keys[0] if pkg.wire_bmad_config_keys else None)
            rows.append(
                Listing(
                    name=pkg.name,
                    kind=KIND_MODULE,
                    source=self.name,
                    trust_tier=TIER_BMAD_CERTIFIED,
                    description=about.get("summary", ""),
                    repository=repository,
                    version=read_recipe_version(ctx.repo_root, pkg.name),
                    code=code,
                    install_hint=(f"steward provision --module {code}" if code else f"pixi add {pkg.name}"),
                    link=about.get("homepage") or repository,
                )
            )
        return rows


class EstateFramesSource(CatalogSourcePlugin):
    """``docs/foundry/frames/`` — each Frame that passes ``frames.preflight_frames``
    (reused, never a second Frame parser) is a ``kind: frame`` listing keyed by
    its ``identifier``; ``unverified`` because the validator is the preflight,
    and promotion is a 60.2 review record.

    Anchor: the declared ``path`` is **repo-root-relative** (the Frames live in
    the repo, outside the edit store; absent/null → ``frames.FRAMES_RELATIVE``).
    """

    @property
    def name(self) -> str:
        return "estate-frames"

    def listings(self, ctx: SourceContext) -> list[Listing]:
        rel = ctx.decl.options.get("path") or None
        frames_root = ctx.repo_root / str(rel) if rel else None
        report = preflight_frames(ctx.repo_root, frames_root=frames_root)
        failed = {finding.path for finding in report.findings}
        repository = f"https://github.com/{ctx.config.edit_store.repo}"
        rows: list[Listing] = []
        for doc in report.frames:
            if doc.path in failed:
                continue
            identifier = doc.fields.get("identifier")
            if not isinstance(identifier, str) or not identifier.strip():
                continue
            try:
                rel_path = doc.path.resolve().relative_to(ctx.repo_root.resolve()).as_posix()
            except ValueError:
                rel_path = doc.path.as_posix()
            version = doc.fields.get("version")
            rows.append(
                Listing(
                    name=identifier.strip(),
                    kind=KIND_FRAME,
                    source=self.name,
                    trust_tier=TIER_UNVERIFIED,
                    description=str(doc.fields.get("description") or ""),
                    repository=repository,
                    version=str(version) if version is not None else None,
                    install_hint=f"load {rel_path}",
                    link=rel_path,
                )
            )
        return rows


def default_sources() -> list[CatalogSourcePlugin]:
    return [EstateListingsSource(), WieldedSuiteSource(), EstateFramesSource()]


# ── default backends (declarations with the shared snapshot interface) ──────


class CondaChannelBackend(ShipBackendPlugin):
    """noarch index package on the estate channel (SelfExplainML locally,
    Artifactory when air-gapped) — the v1 default ship path; 60.3 ships it."""

    @property
    def name(self) -> str:
        return "conda-channel"

    def snapshot_target(self, decl: BackendDecl) -> str:
        # `or`, not a `.get` default: a declared `channel: null` is absent, not "None".
        channel = decl.options.get("channel") or "SelfExplainML"
        package = decl.options.get("package") or "pyforge-estate-catalog"
        return f"conda://{channel}/{package}"


class ObjectStorageBackend(ShipBackendPlugin):
    """The same snapshot as a blob on the consumed S3-style store (Epic 50)."""

    @property
    def name(self) -> str:
        return "object-storage"

    def snapshot_target(self, decl: BackendDecl) -> str:
        bucket = decl.options.get("bucket") or "<bucket>"
        key = decl.options.get("key") or "catalog/snapshot.tar.gz"
        return f"s3://{bucket}/{key}"


class GitBundleBackend(ShipBackendPlugin):
    """The same snapshot as a file (git bundle / tarball)."""

    @property
    def name(self) -> str:
        return "git-bundle"

    def snapshot_target(self, decl: BackendDecl) -> str:
        return str(decl.options.get("file") or "catalog.bundle")


def default_backends() -> list[ShipBackendPlugin]:
    return [CondaChannelBackend(), ObjectStorageBackend(), GitBundleBackend()]


# ── engine ───────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CatalogFinding:
    code: str
    subject: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "subject": self.subject, "message": self.message}


@dataclass(frozen=True)
class CatalogReport:
    """What ``check`` returns — frozen evidence."""

    catalog: dict[str, object]
    backends: tuple[dict[str, object], ...]
    sources: tuple[dict[str, object], ...]
    slots: tuple[str, ...]
    findings: tuple[CatalogFinding, ...]
    listing_count: int

    @property
    def ok(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "catalog": dict(self.catalog),
            "backends": [dict(b) for b in self.backends],
            "sources": [dict(s) for s in self.sources],
            "slots": list(self.slots),
            "findings": [f.to_dict() for f in self.findings],
            "listing_count": self.listing_count,
        }


@dataclass(frozen=True)
class RenderResult:
    """What ``render`` returns: refused (``findings`` non-empty, nothing
    written) or rendered (``manifests`` by relative path, ``written`` paths)."""

    findings: tuple[CatalogFinding, ...]
    manifests: dict[str, str]
    written: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.findings


_REPO_SEGMENT = re.compile(r"^[A-Za-z0-9_.-]+$")


def _github_owner_repo(repository: str | None) -> str | None:
    """``https://github.com/owner/repo[.git][/]`` or bare ``owner/repo`` → ``owner/repo``.

    Exactly two ``/``-separated segments of ``[A-Za-z0-9_.-]+`` — the SSH form
    (``git@github.com:o/r``), fragments/queries (``o/r#readme``), spaces and any
    other host are ``None``, never emitted verbatim as ``source.repo``.
    """
    if not repository:
        return None
    text = repository.strip()
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if text.startswith(prefix):
            text = text[len(prefix) :]
            break
    else:
        if "://" in text:
            return None
    text = text.rstrip("/")
    if text.endswith(".git"):
        text = text[: -len(".git")]
    parts = text.split("/")
    if len(parts) != 2 or not all(_REPO_SEGMENT.match(part) for part in parts):
        return None
    return "/".join(parts)


def _json_text(payload: object) -> str:
    return json.dumps(payload, indent=2) + "\n"


class CatalogEngine:
    """Binds the declared backends/sources to registered plugins, collects
    listings, checks the catalog, renders the two generated manifests."""

    def __init__(
        self,
        repo_root: Path,
        config: CatalogConfig,
        *,
        catalog_dir: Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.config = config
        self.catalog_dir = Path(catalog_dir) if catalog_dir is not None else self.repo_root / CATALOG_RELATIVE
        self.sources = SourceRegistry()
        self.backends = BackendRegistry()
        for source in default_sources():
            self.sources.register(source)
        for backend in default_backends():
            self.backends.register(backend)

    # -- binding --

    def _bound(self, decl: SourceDecl | BackendDecl, registry: _Registry) -> bool:
        return decl.plugin is not None and decl.plugin in registry

    def _bound_sources(self) -> list[tuple[SourceDecl, CatalogSourcePlugin]]:
        return [
            (decl, self.sources.get(decl.plugin))
            for decl in self.config.sources
            if decl.state == STATE_ON and self._bound(decl, self.sources)
        ]

    def _collect(self) -> tuple[list[Listing], list[CatalogFinding]]:
        """Every bound source's rows plus the listing findings.

        A row that names no source or another source (``listing-no-source`` /
        ``listing-source-mismatch``) is reported and **withheld** — it never
        reaches a manifest. A source that raises is one ``config-source``
        finding and the other sources still run (a backend already gets the
        same guard). Two rows with the same ``(kind, name)`` — from two
        sources or one — are ``listing-duplicate``; a module row with no
        repository at all is ``listing-no-repository`` (no manifest source
        form can express it).
        """
        listings: list[Listing] = []
        findings: list[CatalogFinding] = []
        seen: dict[tuple[str, str], str] = {}
        for decl, plugin in self._bound_sources():
            ctx = SourceContext(
                repo_root=self.repo_root,
                catalog_dir=self.catalog_dir,
                config=self.config,
                decl=decl,
            )
            try:
                rows = plugin.listings(ctx)
            except CatalogConfigError as exc:
                findings.append(CatalogFinding("config-source", f"sources.{decl.name}", str(exc)))
                continue
            except Exception as exc:  # noqa: BLE001 — a source must never abort check
                findings.append(CatalogFinding("config-source", f"sources.{decl.name}", f"{type(exc).__name__}: {exc}"))
                continue
            for row in rows:
                if not row.source:
                    findings.append(
                        CatalogFinding(
                            "listing-no-source",
                            row.name,
                            f"listing {row.name!r} from source {decl.name!r} names no source",
                        )
                    )
                    continue
                if row.source != decl.name:
                    findings.append(
                        CatalogFinding(
                            "listing-source-mismatch",
                            row.name,
                            f"listing {row.name!r} names source {row.source!r} but was "
                            f"produced by {decl.name!r}; a listing names exactly one source",
                        )
                    )
                    continue
                key = (row.kind, row.name)
                if key in seen:
                    findings.append(
                        CatalogFinding(
                            "listing-duplicate",
                            row.name,
                            f"{row.kind} {row.name!r} is listed twice: by {seen[key]!r} and by "
                            f"{decl.name!r}; a listing names exactly one source",
                        )
                    )
                else:
                    seen[key] = decl.name
                if row.kind == KIND_MODULE and not (row.repository or "").strip():
                    findings.append(
                        CatalogFinding(
                            "listing-no-repository",
                            row.name,
                            f"module {row.name!r} from {decl.name!r} has no repository; "
                            "no manifest source form can point at it",
                        )
                    )
                listings.append(row)
        return listings, findings

    def listings(self) -> list[Listing]:
        return self._collect()[0]

    # -- manifests --

    @staticmethod
    def _claude_source(repository: str | None) -> dict[str, str] | None:
        """GitHub ``owner/repo`` → the ``github`` form; any other git URL →
        Claude Code's documented ``{"source": "url", "url": …}`` form."""
        repo = _github_owner_repo(repository)
        if repo is not None:
            return {"source": "github", "repo": repo}
        if repository and repository.strip():
            return {"source": "url", "url": repository.strip()}
        return None

    def manifests(self, listings: list[Listing] | None = None) -> dict[str, str]:
        """The two generated manifests, ``{relative path: text}`` — pure; the
        caller decides whether the rows are fit to render (``render``)."""
        rows = self.listings() if listings is None else listings
        cfg = self.config
        claude_plugins: list[dict[str, object]] = []
        for row in rows:
            if row.kind != KIND_MODULE:
                continue
            source = self._claude_source(row.repository)
            if source is None:
                continue  # `listing-no-repository` already refused the render
            entry: dict[str, object] = {
                "name": row.name,
                "description": row.description,
            }
            if row.version:
                entry["version"] = row.version
            entry["source"] = source
            if row.link:
                entry["homepage"] = row.link
            entry["tags"] = [f"source:{row.source}", f"trust:{row.trust_tier}"]
            claude_plugins.append(entry)
        claude = {
            "name": cfg.name,
            "owner": {"name": cfg.owner},
            "metadata": {"description": cfg.description},
            "plugins": claude_plugins,
        }
        codex = {
            "name": cfg.name,
            "interface": {"displayName": cfg.display_name},
            "plugins": [
                {
                    "name": row.name,
                    "source": {"source": "local", "path": row.codex_source},
                    "policy": {"installation": "AVAILABLE"},
                    "category": row.kind,
                }
                for row in rows
                if row.codex_source
            ],
        }
        return {
            CLAUDE_MANIFEST_RELATIVE.as_posix(): _json_text(claude),
            CODEX_MANIFEST_RELATIVE.as_posix(): _json_text(codex),
        }

    def render(self, *, write: bool = False) -> RenderResult:
        """Render both manifests; ``write=True`` puts them beside the config.

        Any collect finding (a raising source, a withheld row, a duplicate, a
        module with no repository) refuses the render: ``ok=False``, the
        findings in the result, nothing written — a manifest must never
        silently lack the rows a broken source would have produced.
        """
        rows, findings = self._collect()
        if findings:
            return RenderResult(findings=tuple(findings), manifests={}, written=())
        manifests = self.manifests(rows)
        written: list[str] = []
        if write:
            for rel, text in manifests.items():
                target = self.catalog_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
                written.append(str(target))
        return RenderResult(findings=(), manifests=manifests, written=tuple(written))

    def _drift_of(self, rows: list[Listing]) -> list[CatalogFinding]:
        """``manifest-drift`` for each generated manifest that is missing or stale."""
        findings: list[CatalogFinding] = []
        for rel, text in self.manifests(rows).items():
            target = self.catalog_dir / rel
            try:
                on_disk = target.read_text(encoding="utf-8")
            except OSError:
                findings.append(
                    CatalogFinding("manifest-drift", rel, f"{target} is missing; run `steward catalog render`")
                )
                continue
            if on_disk != text:
                findings.append(
                    CatalogFinding("manifest-drift", rel, f"{target} is stale; run `steward catalog render`")
                )
        return findings

    def drift(self) -> list[CatalogFinding]:
        """What ``render --check`` reports: the collect findings when there are
        any (a fresh render would refuse, so "in sync" would be a false green),
        else ``manifest-drift`` per missing/stale manifest."""
        rows, findings = self._collect()
        if findings:
            return findings
        return self._drift_of(rows)

    # -- check --

    def check(self) -> CatalogReport:
        findings: list[CatalogFinding] = []
        backends: list[dict[str, object]] = []
        for decl in self.config.backends:
            bound = self._bound(decl, self.backends)
            target: str | None = None
            if bound:
                try:
                    target = self.backends.get(decl.plugin).snapshot_target(decl)
                except Exception as exc:  # noqa: BLE001 — a backend must never abort check
                    findings.append(
                        CatalogFinding("config-backend", f"backends.{decl.name}", f"{type(exc).__name__}: {exc}")
                    )
            elif decl.state == STATE_ON:
                findings.append(
                    CatalogFinding(
                        "slot-unbound",
                        f"backends.{decl.name}",
                        f"state 'on' names plugin {decl.plugin!r} which is not registered "
                        f"(registered backends: {self.backends.names()})",
                    )
                )
            backends.append(
                {
                    "name": decl.name,
                    "plugin": decl.plugin,
                    "state": decl.state,
                    "bound": bound,
                    "snapshot_target": target,
                }
            )

        listings, listing_findings = self._collect()
        findings.extend(listing_findings)
        per_source: dict[str, int] = {}
        for row in listings:
            per_source[row.source] = per_source.get(row.source, 0) + 1
        sources: list[dict[str, object]] = []
        for decl in self.config.sources:
            bound = self._bound(decl, self.sources)
            if not bound and decl.state == STATE_ON:
                findings.append(
                    CatalogFinding(
                        "slot-unbound",
                        f"sources.{decl.name}",
                        f"state 'on' names plugin {decl.plugin!r} which is not registered "
                        f"(registered sources: {self.sources.names()})",
                    )
                )
            sources.append(
                {
                    "name": decl.name,
                    "plugin": decl.plugin,
                    "state": decl.state,
                    "bound": bound,
                    "listings": per_source.get(decl.name, 0),
                }
            )

        # Drift is only meaningful when a fresh render would succeed; with
        # collect findings the manifests on disk are not comparable to a
        # row set that is already missing something.
        if not listing_findings:
            findings.extend(self._drift_of(listings))

        slots = tuple(decl.name for decl in (*self.config.backends, *self.config.sources) if decl.state != STATE_ON)
        store = self.config.edit_store
        return CatalogReport(
            catalog={
                "name": self.config.name,
                "owner": self.config.owner,
                "edit_store": {
                    "kind": store.kind,
                    "repo": store.repo,
                    "path": store.path,
                    "dedicated_repo": store.dedicated_repo,
                },
            },
            backends=tuple(backends),
            sources=tuple(sources),
            slots=slots,
            findings=tuple(findings),
            listing_count=len(listings),
        )

    # -- pointers --

    def pointers(self) -> dict[str, object]:
        """How a consumer points at this catalog today, without editing
        ``.claude/settings.json`` or minting a repo."""
        abs_dir = self.catalog_dir.resolve()
        try:
            rel_dir = abs_dir.relative_to(self.repo_root.resolve()).as_posix()
        except ValueError:
            rel_dir = abs_dir.as_posix()
        name = self.config.name
        dedicated = self.config.edit_store.dedicated_repo
        github_note = (
            f"github forms available: extraKnownMarketplaces source github repo {dedicated}"
            if dedicated
            else (
                "github forms (extraKnownMarketplaces `github`, `codex plugin marketplace add "
                "<owner/repo>`) wait on edit_store.dedicated_repo — no catalog repo is minted "
                "without operator confirm"
            )
        )
        quoted_dir = shlex.quote(str(abs_dir))  # a path with a space must paste intact
        return {
            "catalog_dir": str(abs_dir),
            "custom_source": f"bmad-method install --custom-source {quoted_dir}",
            "extra_known_marketplaces": {
                "extraKnownMarketplaces": {name: {"source": {"source": "directory", "path": rel_dir}}}
            },
            "claude_plugin_add": f"/plugin marketplace add {quoted_dir}",
            "codex_plugin_add": (
                f"codex plugin marketplace add {dedicated}"
                if dedicated
                else "codex plugin marketplace add <owner/repo>  (waits on edit_store.dedicated_repo)"
            ),
            "dedicated_repo": dedicated,
            "github_note": github_note,
            # Verified live 2026-09-19 (bmad-method 6.12.0): the installer resolves
            # this directory ("Local source resolved") but discovery mode installs
            # only module trees inside the source ("Found 0 modules" here) — it does
            # not follow a plugin's `github` source. Pointer rows install from their
            # own `repository` (`install_hint`); Story 60.3's snapshot vendors them.
            "installer_note": (
                "the installer resolves this directory but installs only module trees "
                "inside it (v1 rows are github pointers: 'Found 0 modules'); install a "
                "listed module from its own repository / install_hint until 60.3 ships "
                "the vendored snapshot"
            ),
            "settings_note": ".claude/settings.json is not edited by this duty; paste the block yourself",
        }


# ── duty ─────────────────────────────────────────────────────────────────────


def format_report(report: CatalogReport) -> str:
    slots = ", ".join(report.slots) or "(none)"
    if report.ok:
        return (
            f"catalog check: ok — {len(report.backends)} backends, {len(report.sources)} sources, "
            f"{report.listing_count} listings, {len(report.slots)} slots ({slots})"
        )
    lines = [f"catalog check: {len(report.findings)} finding(s)"]
    for finding in report.findings:
        lines.append(f"  [{finding.code}] {finding.subject}: {finding.message}")
    return "\n".join(lines)


def format_listings(rows: list[Listing]) -> str:
    if not rows:
        return "catalog list: no listings"
    lines = [f"catalog list: {len(rows)} listing(s)"]
    for row in rows:
        lines.append(
            f"  {row.name}  kind={row.kind}  source={row.source}  trust={row.trust_tier}"
            + (f"  version={row.version}" if row.version else "")
        )
    return "\n".join(lines)


def format_pointers(pointers: dict[str, object]) -> str:
    return "\n".join(
        [
            f"catalog dir: {pointers['catalog_dir']}",
            "",
            "BMAD installer (discovery mode reads .claude-plugin/marketplace.json):",
            f"  {pointers['custom_source']}",
            f"  note: {pointers['installer_note']}",
            "",
            "Claude Code — .claude/settings.json (directory form; repo-relative, worktree-safe):",
            json.dumps(pointers["extra_known_marketplaces"], indent=2),
            "",
            "Claude Code — one session:",
            f"  {pointers['claude_plugin_add']}",
            "",
            "Codex (reads .agents/plugins/marketplace.json):",
            f"  {pointers['codex_plugin_add']}",
            "",
            f"note: {pointers['github_note']}",
            f"note: {pointers['settings_note']}",
        ]
    )


class CatalogDuty:
    """``steward catalog check|list|render [--check]|pointers [--json]`` — Story 60.1."""

    name = "catalog"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "catalog_verb", None) or "check"
        as_json = bool(getattr(ns, "json", False))
        try:
            root = repo_root()
            catalog_arg = getattr(ns, "catalog", None)
            catalog_dir = Path(catalog_arg).resolve() if catalog_arg else default_catalog_dir(root)
            try:
                config = load_config(catalog_dir / CONFIG_FILENAME)
            except CatalogConfigError as exc:
                finding = CatalogFinding("config-load", str(catalog_dir / CONFIG_FILENAME), str(exc))
                payload = {"ok": False, "findings": [finding.to_dict()]}
                return DutyResult(
                    ok=False,
                    summary=_json_text(payload).rstrip("\n") if as_json else f"catalog {verb}: {exc}",
                    details=payload,
                )
            engine = CatalogEngine(root, config, catalog_dir=catalog_dir)

            if verb == "check":
                report = engine.check()
                payload = report.to_dict()
                return DutyResult(
                    ok=report.ok,
                    summary=_json_text(payload).rstrip("\n") if as_json else format_report(report),
                    details=payload,
                )
            if verb == "list":
                rows = engine.listings()
                payload = {"count": len(rows), "listings": [row.to_dict() for row in rows]}
                return DutyResult(
                    ok=True,
                    summary=_json_text(payload).rstrip("\n") if as_json else format_listings(rows),
                    details=payload,
                )
            if verb == "render":
                if getattr(ns, "check", False):
                    drift = engine.drift()
                    payload = {"ok": not drift, "findings": [f.to_dict() for f in drift]}
                    if drift:
                        text = "catalog render --check: " + "; ".join(
                            f"[{f.code}] {f.subject}: {f.message}" for f in drift
                        )
                    else:
                        text = "catalog render --check: manifests in sync"
                    return DutyResult(
                        ok=not drift,
                        summary=_json_text(payload).rstrip("\n") if as_json else text,
                        details=payload,
                    )
                rendered = engine.render(write=True)
                payload = {
                    "ok": rendered.ok,
                    "findings": [f.to_dict() for f in rendered.findings],
                    "written": list(rendered.written),
                }
                if rendered.ok:
                    text = "catalog render: wrote " + ", ".join(rendered.written)
                else:
                    text = "catalog render: refused, nothing written — " + "; ".join(
                        f"[{f.code}] {f.subject}: {f.message}" for f in rendered.findings
                    )
                return DutyResult(
                    ok=rendered.ok,
                    summary=_json_text(payload).rstrip("\n") if as_json else text,
                    details=payload,
                )
            if verb == "pointers":
                pointers = engine.pointers()
                return DutyResult(
                    ok=True,
                    summary=_json_text(pointers).rstrip("\n") if as_json else format_pointers(pointers),
                    details=pointers,
                )
            return DutyResult(
                ok=False,
                summary=f"catalog: unknown verb {verb!r}; available verbs are {', '.join(VERBS)}",
            )
        except Exception as exc:  # noqa: BLE001 — duty boundary
            message = f"{type(exc).__name__}: {exc}"
            payload = {
                "ok": False,
                "findings": [CatalogFinding("internal", verb, message).to_dict()],
            }
            return DutyResult(
                ok=False,
                summary=(_json_text(payload).rstrip("\n") if as_json else f"catalog {verb} failed: {message}"),
                details=payload,
            )
