"""pyforge.scribe.catalog — the derived BMAD-estate catalog (spec-pyforge-scribe CAP-32, Story 24.1).

Renders ``docs/reference/bmad-estate-llms-full.md`` from live in-tree sources so
that a session reads ONE current picture of the BMAD Method this repo runs on:

  installed core / modules   `_bmad/_config/manifest.yaml`, `_bmad/_config/skf-manifest.yaml`
  skills by family           every `.claude/skills/*/SKILL.md` frontmatter (`name`, `description`)
  phases and sequence        `_bmad/_config/bmad-help.csv`
  the bmad-suite roster      `recipes/bmad-suite/suite-members.yaml` joined with steward's
                             adoption register (§ 1 members, § 2 skill routing)
  pins                       every `bmad-*` / `mybmad-*` dependency key in `pixi.toml`
  the marshal harness range  `HARNESS_VERSION_RANGE_TEXT` in `harness_bmadloop.py`, read as text
  the release cadence        the numbered step titles in `release-cadence.md`

The catalog DERIVES, never decides (register AD-2): a verdict, a wielder, a
provisioning path or a hazard appears only as read from the register, and a
version that disagrees between the register, `pixi.toml` and the local recipe
is rendered as a disagreement naming its sources -- never resolved here.

Offline by construction: no registry or network call; steward's
``suite pipeline-truth --json`` is an optional input. No ``pyforge.<station>``
internals are imported to read a constant -- the marshal range is a regex over
the file, the manifests are line-based readers over their two fixed shapes
(no YAML dependency), the register is a markdown-table reader.

Drift detection is structured, not byte-exact (OQ-CAP-32-1): each section's
derived facts are digested into a header line
``<!-- bmad-estate-digest: <section>=<sha256[:12]> -->``; ``check()`` re-derives
the facts and names the sections whose digest moved, with their source paths,
so a prose tweak in the template never reds a clone and a moved fact always does.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from pyforge.core.atomic_write import atomic_write_text
from pyforge.core.errors import PyforgeError

CATALOG_RELPATH = Path("docs") / "reference" / "bmad-estate-llms-full.md"
REGENERATE_COMMAND = "pixi run -e pyforge-guild scribe catalog bmad-estate --write"
DETECTOR_NAME = "bmad-estate-check"

MANIFEST_RELPATH = Path("_bmad") / "_config" / "manifest.yaml"
SKF_MANIFEST_RELPATH = Path("_bmad") / "_config" / "skf-manifest.yaml"
HELP_CSV_RELPATH = Path("_bmad") / "_config" / "bmad-help.csv"
SKILLS_RELPATH = Path(".claude") / "skills"
SUITE_MEMBERS_RELPATH = Path("recipes") / "bmad-suite" / "suite-members.yaml"
RECIPES_RELPATH = Path("recipes")
PIXI_RELPATH = Path("pixi.toml")
REGISTER_RELPATH = (
    Path("_bmad-output")
    / "projects"
    / "pyforge-steward"
    / "planning-artifacts"
    / "specs"
    / "spec-bmad-suite-lifecycle"
    / "adoption-register.md"
)
CADENCE_RELPATH = REGISTER_RELPATH.with_name("release-cadence.md")
HARNESS_RELPATH = (
    Path("src")
    / "shared"
    / "packages"
    / "pyforge-marshal"
    / "src"
    / "pyforge"
    / "marshal"
    / "adapters"
    / "harness_bmadloop.py"
)

# Skill families, first match wins. `bmad-agent-builder` is a BMB skill, so the
# explicit BMB set is tested before the `bmad-agent-*` prefix.
_BMB_SKILLS = frozenset(
    {"bmad-bmb-setup", "bmad-module-builder", "bmad-workflow-builder", "bmad-agent-builder", "bmad-eval-runner"}
)
_TEA_SKILLS = frozenset({"bmad-tea", "bmad-teach-me-testing"})
_LABS_CONSENT_SKILLS = frozenset({"mcp-builder", "multi-repo-git-ops", "release-please", "slides-generator"})
FAMILY_BMB = "BMad Builder (bmb)"
FAMILY_TEA = "Test Architect (tea, bmad-testarch-*)"
FAMILY_PERSONAS = "Personas (bmad-agent-*)"
FAMILY_UTILITY = "Utility skills (bmad-os-*)"
FAMILY_CIS = "Creative Intelligence Suite (bmad-cis-*)"
FAMILY_LOOP = "bmad-loop (bmad-loop-*)"
FAMILY_SKF = "Skill Forge (skf-*)"
FAMILY_STATIONS = "PyForge station skills (pyforge-*)"
FAMILY_LABS = "labs-skills, by consent"
FAMILY_CORE = "BMAD core"
FAMILY_BMM = "BMad Method (bmm)"
FAMILY_BMAD_OTHER = "Other bmad-* skills"
FAMILY_OTHER = "Other repo skills"
FAMILY_ORDER = (
    FAMILY_CORE,
    FAMILY_BMM,
    FAMILY_PERSONAS,
    FAMILY_BMB,
    FAMILY_TEA,
    FAMILY_CIS,
    FAMILY_UTILITY,
    FAMILY_LOOP,
    FAMILY_SKF,
    FAMILY_LABS,
    FAMILY_STATIONS,
    FAMILY_BMAD_OTHER,
    FAMILY_OTHER,
)

_DIGEST_RE = re.compile(r"^<!-- bmad-estate-digest: ([a-z_-]+)=([0-9a-f]{12}) -->$", re.MULTILINE)
_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.DOTALL)
_HARNESS_RANGE_RE = re.compile(r'^HARNESS_VERSION_RANGE_TEXT\s*=\s*"([^"]+)"', re.MULTILINE)
_CADENCE_STEP_RE = re.compile(r"^(\d+)\.\s+\*\*(.+?)\*\*", re.MULTILINE)
_MEMBER_CELL_RE = re.compile(r"`([^`]+)`\s*(.*)")
_FLOOR_RE = re.compile(r">=\s*([0-9][^,\s]*)")


class CatalogSourceError(PyforgeError, RuntimeError):
    """A source the catalog derives from cannot be read (exit 2, never a false green)."""


@dataclass(frozen=True)
class Skill:
    name: str
    family: str
    description: str
    path: str


@dataclass(frozen=True)
class Member:
    name: str
    description: str
    notes: str
    deprecated: bool


@dataclass(frozen=True)
class RegisterRow:
    member: str
    version: str
    install_class: str
    wired: str
    verdict: str
    wielder: str
    provisioning: str
    hazards: str
    story: str


@dataclass(frozen=True)
class RoutingRow:
    skills: str
    member: str
    station: str
    story: str


@dataclass(frozen=True)
class Disagreement:
    member: str
    versions: dict[str, str]


@dataclass
class Estate:
    """Every derived fact, grouped by the section that renders it."""

    installed: dict[str, object] = field(default_factory=dict)
    skills: list[Skill] = field(default_factory=list)
    skill_dirs_without_skill_md: list[str] = field(default_factory=list)
    help_rows: list[dict[str, str]] = field(default_factory=list)
    module_docs: dict[str, str] = field(default_factory=dict)
    members: list[Member] = field(default_factory=list)
    register: dict[str, RegisterRow] = field(default_factory=dict)
    routing: list[RoutingRow] = field(default_factory=list)
    pins: dict[str, dict[str, str]] = field(default_factory=dict)
    recipe_versions: dict[str, str] = field(default_factory=dict)
    disagreements: list[Disagreement] = field(default_factory=list)
    harness_range: str = ""
    cadence_steps: list[str] = field(default_factory=list)
    pipeline_truth: dict[str, dict[str, str]] = field(default_factory=dict)

    def section_facts(self) -> dict[str, object]:
        """The digestable facts per section -- prose stays out on purpose."""
        return {
            "installed": self.installed,
            "skills": {
                "skills": [asdict(s) for s in self.skills],
                "no_skill_md": list(self.skill_dirs_without_skill_md),
            },
            "phases": {"rows": self.help_rows, "docs": self.module_docs},
            "suite": {
                "members": [asdict(m) for m in self.members],
                "register": {k: asdict(v) for k, v in sorted(self.register.items())},
                "routing": [asdict(r) for r in self.routing],
                "recipes": self.recipe_versions,
                "disagreements": [asdict(d) for d in self.disagreements],
            },
            "pins": self.pins,
            "harness": {"range": self.harness_range},
            "cadence": {"steps": self.cadence_steps},
            "pipeline-truth": self.pipeline_truth,
        }


# --------------------------------------------------------------------------
# Readers -- each names its source path in the error it raises.
# --------------------------------------------------------------------------


def _read_text(root: Path, rel: Path) -> str:
    path = root / rel
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogSourceError(f"cannot read {rel}: {exc.__class__.__name__}: {exc}") from exc


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        return inner.replace("''", "'") if value[0] == "'" else inner
    return value


def _frontmatter(text: str) -> dict[str, str]:
    """A flat reader for `key: value` frontmatter; a block scalar (`|`, `>`)
    yields its first non-empty continuation line."""
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return {}
    lines = match.group(1).splitlines()
    out: dict[str, str] = {}
    for index, line in enumerate(lines):
        if not line or line[0] in " \t#":
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        value = value.strip()
        if value in ("|", ">", "|-", ">-", "|+", ">+", ""):
            # A block scalar: every indented continuation line, joined with a space.
            parts: list[str] = []
            for cont in lines[index + 1 :]:
                if cont and cont[0] not in " \t":
                    break
                if cont.strip():
                    parts.append(cont.strip())
            value = " ".join(parts)
        out[key.strip()] = _unquote(value)
    return out


def read_installed(root: Path) -> dict[str, object]:
    text = _read_text(root, MANIFEST_RELPATH)
    section = ""
    installation: dict[str, str] = {}
    modules: list[dict[str, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if not raw.startswith(" "):
            section = raw.split(":", 1)[0].strip()
            continue
        stripped = raw.strip()
        if section == "installation":
            key, _, value = stripped.partition(":")
            installation[key.strip()] = _unquote(value)
        elif section == "modules":
            if stripped.startswith("- "):
                key, _, value = stripped[2:].partition(":")
                modules.append({key.strip(): _unquote(value)})
            elif modules:
                key, _, value = stripped.partition(":")
                modules[-1][key.strip()] = _unquote(value)
    if "version" not in installation:
        raise CatalogSourceError(f"{MANIFEST_RELPATH} carries no installation.version")
    skf_text = _read_text(root, SKF_MANIFEST_RELPATH)
    skf: dict[str, str] = {}
    for raw in skf_text.splitlines():
        if raw.startswith("#") or raw.startswith(" ") or ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        if value.strip():
            skf[key.strip()] = _unquote(value)
    return {
        "core_version": installation["version"],
        "install_shims": installation.get("installShims", ""),
        "install_date": installation.get("installDate", ""),
        "last_updated": installation.get("lastUpdated", ""),
        "modules": modules,
        "skf_version": skf.get("version", ""),
        "skf_installed_at": skf.get("installed_at", ""),
    }


def _family_for(name: str, help_modules: dict[str, str]) -> str:
    if name in _BMB_SKILLS:
        return FAMILY_BMB
    if name in _TEA_SKILLS or name.startswith("bmad-testarch-"):
        return FAMILY_TEA
    if name.startswith("bmad-agent-"):
        return FAMILY_PERSONAS
    if name.startswith("bmad-os-"):
        return FAMILY_UTILITY
    if name.startswith("bmad-cis-"):
        return FAMILY_CIS
    if name.startswith("bmad-loop-"):
        return FAMILY_LOOP
    if name.startswith("skf-"):
        return FAMILY_SKF
    if name.startswith("pyforge-"):
        return FAMILY_STATIONS
    if name in _LABS_CONSENT_SKILLS:
        return FAMILY_LABS
    if name.startswith("bmad-"):
        module = help_modules.get(name, "")
        if module.lower() == "core":
            return FAMILY_CORE
        if module:
            return FAMILY_BMM
        return FAMILY_BMAD_OTHER
    return FAMILY_OTHER


def read_help(root: Path) -> tuple[list[dict[str, str]], dict[str, str]]:
    text = _read_text(root, HELP_CSV_RELPATH)
    rows: list[dict[str, str]] = []
    docs: dict[str, str] = {}
    for record in csv.DictReader(io.StringIO(text)):
        skill = (record.get("skill") or "").strip()
        module = (record.get("module") or "").strip()
        if skill == "_meta":
            docs[module] = (record.get("output-location") or "").strip()
            continue
        if not skill:
            continue
        rows.append(
            {
                "module": module,
                "skill": skill,
                "phase": (record.get("phase") or "").strip(),
                "required": (record.get("required") or "").strip(),
                "preceded-by": (record.get("preceded-by") or "").strip(),
                "followed-by": (record.get("followed-by") or "").strip(),
            }
        )
    return rows, docs


def read_skills(root: Path, help_modules: dict[str, str]) -> tuple[list[Skill], list[str]]:
    skills_dir = root / SKILLS_RELPATH
    if not skills_dir.is_dir():
        raise CatalogSourceError(f"{SKILLS_RELPATH} is not a directory")
    skills: list[Skill] = []
    missing: list[str] = []
    for entry in sorted(skills_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            nested = sorted((entry / "active").glob("*/SKILL.md")) if (entry / "active").is_dir() else []
            if not nested:
                missing.append(entry.name)
                continue
            skill_md = nested[0]
        meta = _frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
        name = meta.get("name") or entry.name
        description = " ".join(meta.get("description", "").split())
        skills.append(
            Skill(
                name=name,
                family=_family_for(name, help_modules),
                description=description,
                path=skill_md.relative_to(root).as_posix(),
            )
        )
    return skills, missing


def read_members(root: Path) -> list[Member]:
    text = _read_text(root, SUITE_MEMBERS_RELPATH)
    raw_members: list[dict[str, str]] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- name:"):
            raw_members.append({"name": _unquote(stripped.partition(":")[2])})
            continue
        # A member's own scalar fields sit at exactly four spaces; a url list item sits deeper.
        if not raw_members or not raw.startswith("    ") or raw.startswith("      ") or stripped.startswith("- "):
            continue
        key, _, value = stripped.partition(":")
        if key in ("description", "notes", "deprecated"):
            raw_members[-1][key] = _unquote(value)
    members = [
        Member(
            name=item["name"],
            description=item.get("description", ""),
            notes=item.get("notes", ""),
            deprecated=item.get("deprecated", "").lower() == "true",
        )
        for item in raw_members
        if item.get("name")
    ]
    if not members:
        raise CatalogSourceError(f"{SUITE_MEMBERS_RELPATH} lists no members")
    return members


def _table_rows(text: str, heading_prefix: str) -> list[list[str]]:
    """Cells of every data row in the first markdown table under a `## ` heading."""
    rows: list[list[str]] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line[3:].startswith(heading_prefix)
            continue
        if not in_section or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or cells[0].startswith("---") or cells[0] in ("#", "Skill"):
            continue
        rows.append(cells)
    return rows


def read_register(root: Path) -> tuple[dict[str, RegisterRow], list[RoutingRow]]:
    text = _read_text(root, REGISTER_RELPATH)
    register: dict[str, RegisterRow] = {}
    for cells in _table_rows(text, "1."):
        if len(cells) < 9 or not cells[0].isdigit():
            continue
        match = _MEMBER_CELL_RE.search(cells[1])
        if match is None:
            continue
        register[match.group(1)] = RegisterRow(
            member=match.group(1),
            version=match.group(2).strip(),
            install_class=cells[2],
            wired=cells[3],
            verdict=cells[4],
            wielder=cells[5],
            provisioning=cells[6],
            hazards=cells[7],
            story=cells[8],
        )
    routing = [
        RoutingRow(skills=cells[0], member=cells[1], station=cells[2], story=cells[4])
        for cells in _table_rows(text, "2.")
        if len(cells) >= 5
    ]
    if not register:
        raise CatalogSourceError(f"{REGISTER_RELPATH} § 1 carries no member rows")
    return register, routing


def _walk_pins(node: object, path: tuple[str, ...], out: dict[str, dict[str, str]]) -> None:
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        in_dependency_table = bool(path) and path[-1].endswith("dependencies")
        if in_dependency_table and isinstance(key, str) and (key.startswith("bmad-") or key.startswith("mybmad")):
            spec: str | None = None
            if isinstance(value, str):
                spec = value
            elif isinstance(value, dict) and isinstance(value.get("version"), str):
                spec = str(value["version"])
            if spec is not None:
                out.setdefault(key, {})[".".join(path) or "<root>"] = spec
                continue
        if isinstance(value, dict):
            _walk_pins(value, (*path, str(key)), out)


def read_pins(root: Path) -> dict[str, dict[str, str]]:
    try:
        data = tomllib.loads(_read_text(root, PIXI_RELPATH))
    except tomllib.TOMLDecodeError as exc:
        raise CatalogSourceError(f"{PIXI_RELPATH} is not valid TOML: {exc}") from exc
    pins: dict[str, dict[str, str]] = {}
    _walk_pins(data, (), pins)
    return {name: dict(sorted(tables.items())) for name, tables in sorted(pins.items())}


def read_recipe_versions(root: Path, names: list[str]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in names:
        recipe = root / RECIPES_RELPATH / name / "recipe.yaml"
        if not recipe.is_file():
            continue
        for line in recipe.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("version:"):
                versions[name] = _unquote(stripped.partition(":")[2])
                break
    return versions


def read_harness_range(root: Path) -> str:
    match = _HARNESS_RANGE_RE.search(_read_text(root, HARNESS_RELPATH))
    if match is None:
        raise CatalogSourceError(f"{HARNESS_RELPATH} carries no HARNESS_VERSION_RANGE_TEXT assignment")
    return match.group(1)


def read_cadence_steps(root: Path) -> list[str]:
    steps = [f"{n}. {title}" for n, title in _CADENCE_STEP_RE.findall(_read_text(root, CADENCE_RELPATH))]
    if not steps:
        raise CatalogSourceError(f"{CADENCE_RELPATH} carries no numbered step titles")
    return steps


def read_pipeline_truth(path: Path) -> dict[str, dict[str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CatalogSourceError(f"cannot read pipeline-truth JSON {path}: {exc}") from exc
    packages = data.get("packages", data) if isinstance(data, dict) else data
    out: dict[str, dict[str, str]] = {}
    for pkg in packages if isinstance(packages, list) else []:
        if not isinstance(pkg, dict) or "name" not in pkg:
            continue
        stages: dict[str, str] = {}
        for stage in ("recipe", "channel", "installed", "wired", "upstream_npm", "upstream_github"):
            probe = pkg.get(stage)
            if isinstance(probe, dict):
                stages[stage] = str(probe.get("value", ""))
        stages["drifts"] = ", ".join(str(d) for d in pkg.get("drifts", []))
        out[str(pkg["name"])] = stages
    return out


def _floor(spec: str) -> str:
    match = _FLOOR_RE.search(spec)
    return match.group(1) if match else spec.strip()


def find_disagreements(estate: Estate) -> list[Disagreement]:
    out: list[Disagreement] = []
    for member in estate.members:
        if member.deprecated:
            continue
        versions: dict[str, str] = {}
        row = estate.register.get(member.name)
        if row is not None and row.version:
            versions[REGISTER_RELPATH.as_posix()] = row.version
        floors = {_floor(spec) for spec in estate.pins.get(member.name, {}).values()}
        if floors:
            versions[PIXI_RELPATH.as_posix()] = " / ".join(sorted(floors))
        recipe = estate.recipe_versions.get(member.name)
        if recipe:
            versions[f"recipes/{member.name}/recipe.yaml"] = recipe
        distinct = {v for v in versions.values()}
        if len(distinct) > 1:
            out.append(Disagreement(member=member.name, versions=versions))
    return out


def derive(root: Path, *, pipeline_truth: Path | None = None) -> Estate:
    """Read every source and assemble the facts; raises CatalogSourceError when one cannot be read."""
    root = root.resolve()
    estate = Estate()
    estate.installed = read_installed(root)
    estate.help_rows, estate.module_docs = read_help(root)
    # A skill listed under two modules (bmad-help.csv carries a few) is Core when any row says so.
    help_modules: dict[str, str] = {}
    for row in estate.help_rows:
        if help_modules.get(row["skill"], "").lower() != "core":
            help_modules[row["skill"]] = row["module"]
    estate.skills, estate.skill_dirs_without_skill_md = read_skills(root, help_modules)
    estate.members = read_members(root)
    estate.register, estate.routing = read_register(root)
    estate.pins = read_pins(root)
    estate.recipe_versions = read_recipe_versions(root, [m.name for m in estate.members])
    estate.harness_range = read_harness_range(root)
    estate.cadence_steps = read_cadence_steps(root)
    if pipeline_truth is not None:
        estate.pipeline_truth = read_pipeline_truth(pipeline_truth)
    estate.disagreements = find_disagreements(estate)
    return estate


# --------------------------------------------------------------------------
# Rendering and the structured check.
# --------------------------------------------------------------------------


def digests(estate: Estate) -> dict[str, str]:
    return {
        section: hashlib.sha256(json.dumps(facts, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]
        for section, facts in estate.section_facts().items()
    }


SECTION_SOURCES: dict[str, tuple[str, ...]] = {
    "installed": (MANIFEST_RELPATH.as_posix(), SKF_MANIFEST_RELPATH.as_posix()),
    "skills": (f"{SKILLS_RELPATH.as_posix()}/*/SKILL.md",),
    "phases": (HELP_CSV_RELPATH.as_posix(),),
    "suite": (SUITE_MEMBERS_RELPATH.as_posix(), REGISTER_RELPATH.as_posix(), "recipes/<member>/recipe.yaml"),
    "pins": (PIXI_RELPATH.as_posix(),),
    "harness": (HARNESS_RELPATH.as_posix(),),
    "cadence": (CADENCE_RELPATH.as_posix(),),
    "pipeline-truth": ("steward suite pipeline-truth --json (optional input)",),
}


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip() or "—"


def render(estate: Estate, *, today: date | None = None) -> str:
    today = today or date.today()
    lines: list[str] = []
    add = lines.append
    add("# local-recipes — the BMAD estate, derived (bmad-estate-llms-full.md)")
    add("")
    add("> Purpose: one current picture of the BMAD Method this repository runs on — the installed")
    add("> core and modules, every skill by family, the bmad-suite roster with its wielding station")
    add("> and provisioning path, the pins, the marshal↔bmad-loop harness range and the release")
    add("> cadence — so a session never acts on a retired skill name or a hand-carried version.")
    add(">")
    add("> **Generated, never hand-written** (`spec-pyforge-scribe` CAP-32). Every fact below is")
    add("> read from the source named beside it; a verdict, wielder or hazard is only ever quoted")
    add("> from steward's adoption register (AD-2), and a version the sources disagree on is shown")
    add("> as a disagreement, never resolved here.")
    add(">")
    add(f"> Generated: {today.isoformat()}. Regenerate: `{REGENERATE_COMMAND}`.")
    add(f"> Drift detector: `pixi run -e pyforge-guild {DETECTOR_NAME}` (structured: a section reds when")
    add("> its derived facts move, prose is exempt).")
    add("")
    for section, digest in digests(estate).items():
        add(f"<!-- bmad-estate-digest: {section}={digest} -->")
    add("")
    # 1 installed
    inst = estate.installed
    add("## 1. Installed core and modules")
    add("")
    add(f"Source: `{MANIFEST_RELPATH.as_posix()}`, `{SKF_MANIFEST_RELPATH.as_posix()}`.")
    add("")
    add(
        f"- **bmad-method core:** `{inst['core_version']}` — `installShims: {inst['install_shims']}`; "
        f"installed {inst['install_date']}, last updated {inst['last_updated']}."
    )
    add(f"- **Skill Forge (skf):** `{inst['skf_version']}`, installed {inst['skf_installed_at']}.")
    add("")
    add("| Module | Version | Source |")
    add("|---|---|---|")
    modules_raw = inst["modules"]
    for mod in modules_raw if isinstance(modules_raw, list) else []:
        add(f"| `{mod.get('name', '')}` | {_cell(mod.get('version', ''))} | {_cell(mod.get('source', ''))} |")
    add("")
    # 2 skills
    add("## 2. Skills by family")
    add("")
    add(f"Source: `{SKILLS_RELPATH.as_posix()}/*/SKILL.md` frontmatter (`name`, `description`); the")
    add(f"core/bmm split comes from `{HELP_CSV_RELPATH.as_posix()}`. {len(estate.skills)} skills.")
    add("")
    by_family: dict[str, list[Skill]] = {}
    for skill in estate.skills:
        by_family.setdefault(skill.family, []).append(skill)
    for family in FAMILY_ORDER:
        members = by_family.get(family)
        if not members:
            continue
        add(f"### {family} ({len(members)})")
        add("")
        add("| Skill | Description |")
        add("|---|---|")
        for skill in members:
            add(f"| `{skill.name}` | {_cell(skill.description[:220])} |")
        add("")
    if estate.skill_dirs_without_skill_md:
        add(
            "Directories under `.claude/skills/` with no `SKILL.md` (not skills): "
            + ", ".join(f"`{d}`" for d in estate.skill_dirs_without_skill_md)
            + "."
        )
        add("")
    # 3 phases
    add("## 3. BMAD phases and sequence")
    add("")
    add(f"Source: `{HELP_CSV_RELPATH.as_posix()}` (installer-generated; what `bmad-help` reads).")
    for module, url in sorted(estate.module_docs.items()):
        add(f"Module docs — {module}: <{url}>.")
    add("")
    add("| Skill | Module | Phase | Required | Preceded by | Followed by |")
    add("|---|---|---|---|---|---|")
    for row in estate.help_rows:
        add(
            f"| `{row['skill']}` | {_cell(row['module'])} | {_cell(row['phase'])} | {_cell(row['required'])} "
            f"| {_cell(row['preceded-by'])} | {_cell(row['followed-by'])} |"
        )
    add("")
    # 4 suite
    active = [m for m in estate.members if not m.deprecated]
    deprecated = [m for m in estate.members if m.deprecated]
    add("## 4. The bmad-suite roster")
    add("")
    add(f"Source: `{SUITE_MEMBERS_RELPATH.as_posix()}` (the population) joined with")
    add(f"`{REGISTER_RELPATH.as_posix()}` § 1 (verdict, wielder, provisioning path, hazards — quoted,")
    add(f"never re-decided) and each member's `recipes/<member>/recipe.yaml`. {len(active)} active members.")
    add("")
    add(
        "| Member | Register version | Install class | Verdict | Wielder | Provisioning path | Hazards | Local recipe |"
    )
    add("|---|---|---|---|---|---|---|---|")
    for member in active:
        reg = estate.register.get(member.name)
        recipe = estate.recipe_versions.get(member.name, "")
        if reg is None:
            add(f"| `{member.name}` | — | — | *(no register row)* | — | — | — | {_cell(recipe)} |")
            continue
        add(
            f"| `{member.name}` | {_cell(reg.version)} | {_cell(reg.install_class)} | {_cell(reg.verdict)} "
            f"| {_cell(reg.wielder)} | {_cell(reg.provisioning)} | {_cell(reg.hazards)} | {_cell(recipe)} |"
        )
    add("")
    if deprecated:
        add(
            "Deprecated catalog rows (kept for drift completeness, never a metapackage run-dep): "
            + ", ".join(f"`{m.name}`" for m in deprecated)
            + "."
        )
        add("")
    add("### Sources disagree")
    add("")
    if estate.disagreements:
        add("| Member | " + " | ".join("Source" for _ in range(3)) + " |")
        add("|---|---|---|---|")
        for item in estate.disagreements:
            cells = [f"`{src}` → {ver}" for src, ver in item.versions.items()]
            while len(cells) < 3:
                cells.append("—")
            add(f"| `{item.member}` | " + " | ".join(_cell(c) for c in cells[:3]) + " |")
        add("")
        add("Rendered as read; the reconcile is steward's (a deferred-work row), never this generator's.")
    else:
        add("None: every active member's register version, `pixi.toml` floor and local recipe agree.")
    add("")
    add("### Skill routing (register § 2 — one wielding station per adopted skill)")
    add("")
    add("| Skill(s) | Source member | Wielding station | Story |")
    add("|---|---|---|---|")
    for route in estate.routing:
        add(f"| {_cell(route.skills)} | {_cell(route.member)} | {_cell(route.station)} | {_cell(route.story)} |")
    add("")
    # 5 pins
    add("## 5. Pins (`bmad-*` in `pixi.toml`)")
    add("")
    add(f"Source: `{PIXI_RELPATH.as_posix()}` — every dependency table that names a `bmad-*` / `mybmad-*` key.")
    add("")
    add("| Package | Table | Spec |")
    add("|---|---|---|")
    for name, tables in estate.pins.items():
        for table, spec in tables.items():
            add(f"| `{name}` | `{table}` | `{spec}` |")
    add("")
    # 6 harness
    add("## 6. Marshal ↔ bmad-loop harness")
    add("")
    add(f"Source: `{HARNESS_RELPATH.as_posix()}` (`HARNESS_VERSION_RANGE_TEXT`, read as text).")
    add("")
    add(f"- Supported bmad-loop range: `{estate.harness_range}`.")
    add("- Marshal wraps bmad-loop through that one module (import-linter enforced); `.bmad-loop/policy.toml`")
    add("  is a derived, gitignored artifact rendered from Marshal's policy fold, never hand-edited.")
    add("")
    # 7 cadence
    add("## 7. The release cadence")
    add("")
    add(f"Source: `{CADENCE_RELPATH.as_posix()}` (the numbered step titles; owner → verb).")
    add("")
    for step in estate.cadence_steps:
        add(f"- {step}")
    add("")
    # 8 pipeline truth
    add("## 8. Pipeline truth (optional input)")
    add("")
    if estate.pipeline_truth:
        add("Source: the `steward suite pipeline-truth --json` file passed with `--pipeline-truth`.")
        add("")
        add("| Member | Recipe | Channel | Installed | Wired | Upstream npm | Upstream GitHub | Drifts |")
        add("|---|---|---|---|---|---|---|---|")
        for name, stages in sorted(estate.pipeline_truth.items()):
            add(
                f"| `{name}` | {_cell(stages.get('recipe', ''))} | {_cell(stages.get('channel', ''))} "
                f"| {_cell(stages.get('installed', ''))} | {_cell(stages.get('wired', ''))} "
                f"| {_cell(stages.get('upstream_npm', ''))} | {_cell(stages.get('upstream_github', ''))} "
                f"| {_cell(stages.get('drifts', ''))} |"
            )
    else:
        add("Not rendered: pass `--pipeline-truth <file>` (the output of `steward suite pipeline-truth --json`)")
        add("to add the six-stage columns. The generator itself makes no network call.")
    add("")
    return "\n".join(lines)


def write(root: Path, *, output: Path | None = None, pipeline_truth: Path | None = None) -> Path:
    estate = derive(root, pipeline_truth=pipeline_truth)
    target = output if output is not None else root / CATALOG_RELPATH
    atomic_write_text(target, render(estate))
    return target


def recorded_digests(text: str) -> dict[str, str]:
    return {section: digest for section, digest in _DIGEST_RE.findall(text)}


def check(root: Path, *, catalog: Path | None = None, pipeline_truth: Path | None = None) -> list[str]:
    """Return one finding per drifted section (empty means current); raises CatalogSourceError."""
    estate = derive(root, pipeline_truth=pipeline_truth)
    target = catalog if catalog is not None else root / CATALOG_RELPATH
    if not target.is_file():
        return [f"catalog missing: {target} — run `{REGENERATE_COMMAND}`"]
    recorded = recorded_digests(target.read_text(encoding="utf-8"))
    findings: list[str] = []
    for section, digest in digests(estate).items():
        if recorded.get(section) != digest:
            sources = ", ".join(SECTION_SOURCES.get(section, ()))
            findings.append(f"section `{section}` drifted (sources: {sources}) — run `{REGENERATE_COMMAND}`")
    return findings
