"""Stories 122.3 and 122.4 (spec-pyforge-steward:CAP-179): steward's help, output, comments and docstrings cite
today's capability ids.

The Specs steward absorbed on 2026-09-17 kept their own numbering in steward's strings: `steward --help` named pin
fan-out and prove-landed by the core-upgrade Spec's ids four and five, which ``SPEC.md`` now calls
``spec-pyforge-steward CAP-12`` and ``spec-pyforge-steward CAP-13``, and report, journal and PR-body strings did the
same, so a reader who looked an id up landed on another capability (today's ``spec-pyforge-steward CAP-4`` is the
budget duty, not pin fan-out). Help and output are public contract (CAP-179). This module holds every capability id in
steward's non-docstring string constants to today's ids, and fails, naming the module, the line and the id, when:

* a bare ``CAP-n`` (or one qualified with ``spec-pyforge-steward``) is not an id ``SPEC.md`` defines, or is not in
  the citing module's allowed set: the capabilities whose ``oracle-map.md`` row names that module among its source
  modules (Story 123.1, spec-pyforge-steward:CAP-181);
* a qualified id names no live Spec: ``spec-<x>:CAP-n`` (or ``spec-<x> CAP-n``) needs a ``spec-<x>/SPEC.md`` outside
  ``archive/``, and ``<prefix>:CAP-n`` needs a prefix ``CHAIN-STANDARD.md`` § 0 lists or one a live Spec declares
  for its own ids (``cite this Spec's ids as `fnd:CAP-N```);
* a ``_HELP`` string in ``cli.py`` cites a capability that no ``contract.md`` row of that duty carries;
* a line changed on the branch (``origin/main...HEAD`` plus the working tree, under the steward package) re-keys an
  id other than by the Spec's provenance map: a re-key from ``CAP-old`` to ``CAP-new`` is valid only when the
  ``SPEC.md`` heading of ``CAP-new`` reads ``<- spec-<absorbed> CAP-old`` and that absorbed Spec is in the module's
  family list (``MODULE_FAMILIES``). This catches a re-key inside one family that picks the wrong sibling
  (``spec-pyforge-steward CAP-12`` for ``spec-pyforge-steward CAP-13``), which the allowed set alone does not. A
  re-key line is one whose text, with every capability and architecture citation masked, is unchanged; it skips
  loudly when ``origin/main`` is not in the checkout. Two rewrites keep a line's meaning and are not re-keys: a bare
  id qualified, same number, with the Spec it always named (the atomic write's bare id becomes
  ``spec-pyforge-core CAP-2``), and a run of adjacent ids that all re-key to one of today's ids, written once (an
  absorbed id beside its new id, ``spec-<absorbed> CAP-old / spec-pyforge-steward CAP-new``, becomes
  ``spec-pyforge-steward CAP-new``).

Story 122.4 adds the comment and docstring domain: every comment (read with ``tokenize``) and every docstring (read
with ``ast``) of every ``.py`` under the package's ``src`` and ``tests``. There a bare ``CAP-n`` is the module's own
capability: one ``SPEC.md`` defines and the module's allowed set holds (for a source module its oracle-map source
modules, as above; for a test module the capabilities whose oracle-map row names it under *Tests*). A comment that
cites another capability qualifies it, ``spec-pyforge-steward CAP-n``, which needs only to be defined; a range's end
takes its start's qualifier (``spec-pyforge-steward CAP-9..CAP-13``). Qualified ids of other Specs and prefixes are
held as in string constants. Package data comments are held by the story's grep, not here.

The ``fires`` tests plant one fault each and prove the checker names it. The module reads ``SPEC.md``,
``contract.md``, ``oracle-map.md``, ``CHAIN-STANDARD.md`` and the live Specs, so it is a live-tree test; the repository
root is found inside a function, never at import.
"""

from __future__ import annotations

import ast
import difflib
import fnmatch
import functools
import io
import re
import subprocess
import tokenize
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.live_tree

STEWARD_PACKAGE = "src/shared/packages/pyforge-steward"
SOURCE_ROOT = f"{STEWARD_PACKAGE}/src/pyforge/steward"
STEWARD_SPEC = "spec-pyforge-steward"
STEWARD_SPEC_DIR = f"_bmad-output/projects/pyforge-steward/planning-artifacts/specs/{STEWARD_SPEC}"
CHAIN_STANDARD = "docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md"
#: Where a live Spec's ``SPEC.md`` sits; anything under ``archive/`` is not live.
LIVE_SPEC_GLOBS: tuple[str, ...] = (
    "_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md",
    "docs/governance/spec-*/SPEC.md",
)
ORIGIN_MAIN = "refs/remotes/origin/main"

#: Module glob (relative to the steward package root) -> the absorbed Specs whose ids that module's lines may be
#: re-keyed from. A re-key in a module no glob matches, or from a Spec its list lacks, is a finding.
MODULE_FAMILIES: dict[str, tuple[str, ...]] = {
    "src/pyforge/steward/cli.py": (
        "spec-bmad-method-core-upgrade",
        "spec-bmad-suite-channel-product",
        "spec-secure-live-dashboards",
        "spec-bmad-suite-install-class-wiring",
        "spec-intelligence-hub",
        "spec-scratch-worktree-lifecycle",
        "spec-vocabulary-one-name-one-job",
    ),
    "src/pyforge/steward/upgrade.py": ("spec-bmad-method-core-upgrade", "spec-bmad-suite-channel-product"),
    "src/pyforge/steward/suite.py": ("spec-bmad-suite-channel-product", "spec-bmad-suite-install-class-wiring"),
    "src/pyforge/steward/suite_advance.py": ("spec-bmad-suite-channel-product",),
    "src/pyforge/steward/deploy.py": ("spec-secure-live-dashboards",),
    "src/pyforge/steward/dashboard/*.py": ("spec-secure-live-dashboards",),
    "src/pyforge/steward/dashboard/models.py": ("spec-work-passports-dated-extracts",),
    "src/pyforge/steward/dashboard/views_htmx.py": (
        "spec-work-passports-dated-extracts",
        "spec-sprint-ledger-query-module",
    ),
    "src/pyforge/steward/fresh_clone.py": ("spec-bmad-suite-install-class-wiring",),
    "src/pyforge/steward/provision.py": (
        "spec-bmad-suite-channel-product",
        "spec-bmad-suite-install-class-wiring",
        "spec-bmad-suite-lifecycle",
    ),
    "src/pyforge/steward/corridor.py": ("spec-work-passports-dated-extracts",),
    "src/pyforge/steward/glass.py": ("spec-work-passports-dated-extracts",),
    "src/pyforge/steward/passport.py": ("spec-work-passports-dated-extracts",),
    "src/pyforge/steward/quarantine.py": ("spec-work-passports-dated-extracts",),
    "src/pyforge/steward/catalog.py": ("spec-self-hosted-bmad-marketplace",),
    "src/pyforge/steward/frames.py": ("spec-intelligence-hub",),
    "src/pyforge/steward/guards.py": ("spec-intelligence-hub",),
    "src/pyforge/steward/track.py": ("spec-intelligence-hub",),
    "src/pyforge/steward/measures.py": ("spec-build-league-scorecard",),
    "src/pyforge/steward/deck_integrity.py": ("spec-vocabulary-one-name-one-job",),
    "src/pyforge/steward/sprint_ledger_query.py": ("spec-sprint-ledger-query-module",),
    "src/pyforge/steward/sync.py": ("spec-jira-github-projects-sync",),
    "src/pyforge/steward/workspace.py": ("spec-scratch-worktree-lifecycle", "spec-multi-repo-workspaces"),
    "src/pyforge/steward/data/bmad_core_releases/*.yaml": ("spec-bmad-method-core-upgrade",),
    "src/pyforge/steward/data/track.schema.json": ("spec-intelligence-hub",),
    "tests/unit/test_upgrade_*.py": ("spec-bmad-method-core-upgrade",),
    "tests/unit/test_upgrade_native_path_spot_checks.py": ("spec-bmad-suite-channel-product",),
    "tests/unit/test_fresh_clone_*.py": ("spec-bmad-suite-install-class-wiring",),
    "tests/unit/test_provision_install_class_playbook.py": ("spec-bmad-suite-install-class-wiring",),
    "tests/unit/test_provision_list_modules.py": ("spec-bmad-suite-channel-product",),
    "tests/unit/test_suite_wired_class_predicates.py": ("spec-bmad-suite-install-class-wiring",),
    "tests/unit/test_suite_advance.py": ("spec-bmad-suite-channel-product",),
    "tests/unit/test_suite_pipeline_truth.py": ("spec-bmad-suite-channel-product",),
    "tests/unit/test_dashboard_*.py": ("spec-secure-live-dashboards",),
    "tests/unit/test_deploy_perimeter.py": ("spec-secure-live-dashboards",),
    "tests/unit/test_deploy_static.py": ("spec-secure-live-dashboards",),
    "tests/meta/test_invariants.py": ("spec-secure-live-dashboards",),
    "tests/meta/test_adoption_register.py": ("spec-bmad-suite-lifecycle",),
    "tests/meta/test_release_cadence_runbook.py": ("spec-bmad-suite-lifecycle",),
    "tests/unit/test_catalog.py": ("spec-self-hosted-bmad-marketplace",),
    "tests/unit/test_guards.py": ("spec-intelligence-hub",),
    "tests/unit/test_track.py": ("spec-intelligence-hub",),
    "tests/unit/test_quarantine.py": ("spec-work-passports-dated-extracts",),
    "tests/unit/test_sprint_ledger_query.py": ("spec-sprint-ledger-query-module",),
    "tests/unit/test_sync_reconcile_propagation.py": ("spec-jira-github-projects-sync",),
    "tests/unit/test_workspace.py": ("spec-scratch-worktree-lifecycle",),
}

#: One capability citation: ``CAP-n``, ``CAP-n/m/k``, ``spec-<x>:CAP-n``, ``spec-<x> CAP-n`` or ``<prefix>:CAP-n``.
_CITATION = re.compile(
    r"(?<![\w-])(?:(?P<spec>spec-[a-z0-9]+(?:-[a-z0-9]+)*)[: ]|(?P<prefix>[a-z]+):)?"
    r"CAP-(?P<number>\d+)(?P<more>(?:/\d+)+)?(?!\d)"
)
#: An architecture-decision citation, masked with the capability ones when a changed line is matched to its old text.
_AD_CITATION = re.compile(r"(?<![\w-])(?:[a-z]+:)?AD-\d+(?!\d)")
_SPEC_HEADING = re.compile(r"^- \*\*CAP-(\d+) — ", re.MULTILINE)
_PROVENANCE = re.compile(r"^- \*\*CAP-(\d+) — .*?\*\* ← (spec-[a-z0-9-]+) CAP-(\d+)(?!\d)", re.MULTILINE)
_DECLARED_ALIAS = re.compile(r"ids as `?([a-z]+):CAP-")
_CONTRACT_ID = re.compile(r"(?<![\w-])(?:(spec-[a-z0-9-]+):)?CAP-(\d+)(?!\d)")
_TICK = re.compile(r"`([^`]+)`")
_HEADING = re.compile(r"^## (.+?)\s*$")
_SEPARATOR_CELL = re.compile(r"^:?-+:?$")
_HUNK = re.compile(r"^@@ ")


# --------------------------------------------------------------------------- where things are


@functools.cache
def _repo_root() -> Path:
    """The checkout this test reads, resolved inside a function and never at import (the live-tree split rule)."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pixi.toml").is_file() and (candidate / SOURCE_ROOT).is_dir():
            return candidate
    raise AssertionError("could not locate the repository root (pixi.toml beside the steward package)")


def _read(rel: str) -> str:
    return (_repo_root() / rel).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- reading a citation


@dataclass(frozen=True)
class Citation:
    """One capability id as written: its qualifier (a Spec name or a prefix, or neither) and its number."""

    spec: str | None
    prefix: str | None
    number: int

    @property
    def steward(self) -> bool:
        """A bare id, or one qualified with steward's own Spec, is a steward capability."""
        return self.prefix is None and self.spec in (None, STEWARD_SPEC)

    def text(self) -> str:
        if self.spec:
            return f"{self.spec} CAP-{self.number}"
        if self.prefix:
            return f"{self.prefix}:CAP-{self.number}"
        return f"CAP-{self.number}"


def citations(text: str) -> list[Citation]:
    """Every capability id ``text`` cites, in order; ``spec-pyforge-steward CAP-2/6/7`` is three."""
    found: list[Citation] = []
    for match in _CITATION.finditer(text):
        numbers = [match.group("number"), *(match.group("more") or "").split("/")[1:]]
        for number in numbers:
            found.append(Citation(match.group("spec"), match.group("prefix"), int(number)))
    return found


def written_citations(text: str) -> list[Citation]:
    """``citations``, except that a range's end takes its start's qualifier: in
    ``spec-pyforge-steward CAP-9..CAP-13`` both ends are qualified."""
    found: list[Citation] = []
    previous_end, qualifier = -1, (None, None)
    for match in _CITATION.finditer(text):
        spec, prefix = match.group("spec"), match.group("prefix")
        if spec is None and prefix is None and text[previous_end : match.start()] == "..":
            spec, prefix = qualifier
        numbers = [match.group("number"), *(match.group("more") or "").split("/")[1:]]
        found.extend(Citation(spec, prefix, int(number)) for number in numbers)
        previous_end, qualifier = match.end(), (spec, prefix)
    return found


def mask(text: str) -> str:
    """``text`` with every capability and architecture citation replaced by one placeholder each."""
    return _AD_CITATION.sub("AD-#", _CITATION.sub("CAP-#", text))


def _docstring_ids(tree: ast.AST) -> set[int]:
    nodes = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    return {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, nodes)
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }


def string_constants(source: str) -> list[tuple[int, str]]:
    """``(line, value)`` for every str constant of a module that is not a docstring (f-string parts included)."""
    tree = ast.parse(source)
    docstrings = _docstring_ids(tree)
    return sorted(
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
    )


def comment_and_docstring_lines(source: str) -> list[tuple[int, str]]:
    """``(line, text)`` for every comment of a module (read with ``tokenize``) and every line of each of its
    docstrings (read with ``ast``)."""
    found = [
        (token.start[0], token.string)
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.COMMENT
    ]
    tree = ast.parse(source)
    docstrings = _docstring_ids(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) in docstrings:
            found.extend((node.lineno + offset, text) for offset, text in enumerate(node.value.splitlines()))
    return sorted(found)


# --------------------------------------------------------------------------- reading the Specs


@dataclass(frozen=True)
class Spec:
    """What the citations are judged against, read from the tree (or planted by a ``fires`` test)."""

    defined: frozenset[int]
    provenance: dict[int, tuple[str, int]]
    allowed: dict[str, frozenset[int]]
    live_specs: frozenset[str]
    prefixes: frozenset[str]
    aliases: dict[str, str]
    duty_capabilities: dict[str, frozenset[str]]
    tested: dict[str, frozenset[int]]

    def allowed_for(self, module: str) -> frozenset[int]:
        """The capabilities whose oracle-map row names ``module`` (relative to the steward source root)."""
        return frozenset(
            number
            for pattern, numbers in self.allowed.items()
            if fnmatch.fnmatchcase(module, pattern)
            for number in numbers
        )

    def allowed_for_path(self, path: str) -> frozenset[int]:
        """A file's own capabilities (``path`` relative to the steward package root): a source module's oracle-map
        source-module rows, a test module's oracle-map *Tests* rows, nothing for any other file."""
        source_root = SOURCE_ROOT.removeprefix(STEWARD_PACKAGE + "/") + "/"
        if path.startswith(source_root):
            return self.allowed_for(path.removeprefix(source_root))
        if path.startswith("tests/"):
            module = path.removeprefix("tests/")
            return frozenset(
                number
                for pattern, numbers in self.tested.items()
                if fnmatch.fnmatchcase(module, pattern)
                for number in numbers
            )
        return frozenset()

    def canonical(self, citation: Citation) -> str:
        """``CAP-n`` for a steward id, ``spec-<x>:CAP-n`` for another Spec's (a declared prefix resolved)."""
        if citation.steward:
            return f"CAP-{citation.number}"
        if citation.spec:
            return f"{citation.spec}:CAP-{citation.number}"
        assert citation.prefix is not None
        spec = self.aliases.get(citation.prefix)
        if spec == STEWARD_SPEC:
            return f"CAP-{citation.number}"
        return f"{spec}:CAP-{citation.number}" if spec else f"{citation.prefix}:CAP-{citation.number}"


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def tables(text: str) -> dict[str, list[dict[str, str]]]:
    """``##`` heading -> its table rows, each a ``{column: cell}`` map."""
    found: dict[str, list[dict[str, str]]] = {}
    heading: str | None = None
    header: list[str] | None = None
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            heading, header = match.group(1), None
            continue
        if heading is None or not line.lstrip().startswith("|"):
            if not line.strip():
                header = None
            continue
        cells = _cells(line)
        if header is None:
            header = cells
            continue
        if all(_SEPARATOR_CELL.match(cell) for cell in cells if cell):
            continue
        found.setdefault(heading, []).append(dict(zip(header, cells, strict=False)))
    return found


def allowed_sets(map_text: str, column: str = "Source modules") -> dict[str, frozenset[int]]:
    """Pattern in ``column`` -> the steward capabilities whose ``oracle-map.md`` row names it (the source modules by
    default; ``Tests`` for the test modules, there relative to the steward ``tests/`` root)."""
    allowed: dict[str, set[int]] = {}
    for row in tables(map_text).get("Capabilities", []):
        match = re.fullmatch(r"CAP-(\d+)(?:\.\.CAP-(\d+))?", row.get("Capability", "").strip())
        if not match:
            continue
        first = int(match.group(1))
        last = int(match.group(2) or first)
        for token in _TICK.findall(row.get(column, "")):
            allowed.setdefault(token.strip(), set()).update(range(first, last + 1))
    return {pattern: frozenset(numbers) for pattern, numbers in allowed.items()}


def duty_capabilities(contract_text: str) -> dict[str, frozenset[str]]:
    """Duty (the verb after ``steward``) -> the canonical capability ids its ``contract.md`` verb rows carry."""
    duties: dict[str, set[str]] = {}
    for row in tables(contract_text).get("CLI verbs and flags", []):
        paths = _TICK.findall(row.get("Verb path", ""))
        if not paths:
            continue
        words = paths[0].split()
        if len(words) < 2 or words[0] != "steward":
            continue
        ids = duties.setdefault(words[1], set())
        for spec, number in _CONTRACT_ID.findall(row.get("Capability", "")):
            ids.add(f"CAP-{number}" if spec in ("", STEWARD_SPEC) else f"{spec}:CAP-{number}")
    return {duty: frozenset(ids) for duty, ids in duties.items()}


def chain_standard_prefixes(text: str) -> frozenset[str]:
    """The citation prefixes ``CHAIN-STANDARD.md`` § 0 lists (the row whose first cell starts with ```AD-n```)."""
    for line in text.splitlines():
        cells = _cells(line) if line.lstrip().startswith("|") else []
        if cells and cells[0].startswith("`AD-n`"):
            return frozenset(re.findall(r"`([a-z]+):`", cells[0]))
    return frozenset()


def live_spec_texts() -> dict[str, str]:
    """Live Spec name -> its ``SPEC.md`` text (never a Spec under ``archive/``)."""
    root = _repo_root()
    found: dict[str, str] = {}
    for pattern in LIVE_SPEC_GLOBS:
        for path in sorted(root.glob(pattern)):
            found[path.parent.name] = path.read_text(encoding="utf-8")
    return found


@functools.cache
def live_spec() -> Spec:
    spec_text = _read(f"{STEWARD_SPEC_DIR}/SPEC.md")
    map_text = _read(f"{STEWARD_SPEC_DIR}/oracle-map.md")
    specs = live_spec_texts()
    aliases: dict[str, str] = {}
    for name, text in specs.items():
        for prefix in _DECLARED_ALIAS.findall(text):
            aliases.setdefault(prefix, name)
    return Spec(
        defined=frozenset(int(number) for number in _SPEC_HEADING.findall(spec_text)),
        provenance={
            int(new): (absorbed, int(old))
            for new, absorbed, old in _PROVENANCE.findall(spec_text)
            if absorbed != STEWARD_SPEC
        },
        allowed=allowed_sets(map_text),
        live_specs=frozenset(specs),
        prefixes=chain_standard_prefixes(_read(CHAIN_STANDARD)),
        aliases=aliases,
        duty_capabilities=duty_capabilities(_read(f"{STEWARD_SPEC_DIR}/contract.md")),
        tested=allowed_sets(map_text, "Tests"),
    )


# --------------------------------------------------------------------------- the checks


def _qualifier_finding(where: str, citation: Citation, spec: Spec) -> str | None:
    """Why another Spec's id (or a prefixed one) does not resolve, or None when it does."""
    if citation.spec and citation.spec not in spec.live_specs:
        return f"{where} names no live Spec"
    if citation.prefix and citation.prefix not in spec.prefixes and citation.prefix not in spec.aliases:
        return f"{where}: the prefix `{citation.prefix}:` is neither in CHAIN-STANDARD.md nor declared"
    return None


def citation_findings(module: str, source: str, spec: Spec) -> list[str]:
    """Every fault of the ids ``module``'s non-docstring string constants cite (``module`` relative to the source root)."""
    findings: list[str] = []
    allowed = spec.allowed_for(module)
    for line, value in string_constants(source):
        for citation in citations(value):
            where = f"{module}:{line}: `{citation.text()}`"
            if citation.steward:
                if citation.number not in spec.defined:
                    findings.append(f"{where} is not an id SPEC.md defines")
                elif citation.number not in allowed:
                    findings.append(f"{where} is not in {module}'s allowed set (no oracle-map.md row names it)")
            else:
                finding = _qualifier_finding(where, citation, spec)
                if finding:
                    findings.append(finding)
    return findings


def comment_findings(path: str, source: str, spec: Spec) -> list[str]:
    """Every fault of the ids ``path``'s comments and docstrings cite (``path`` relative to the steward package root):
    a bare id must be defined and the file's own (``Spec.allowed_for_path``); one qualified with steward's Spec must
    be defined; another Spec's id must resolve."""
    findings: list[str] = []
    allowed = spec.allowed_for_path(path)
    for line, text in comment_and_docstring_lines(source):
        for citation in written_citations(text):
            where = f"{path}:{line}: `{citation.text()}`"
            if citation.steward:
                if citation.number not in spec.defined:
                    findings.append(f"{where} is not an id SPEC.md defines")
                elif citation.spec is None and citation.number not in allowed:
                    findings.append(
                        f"{where} is not in {path}'s allowed set (no oracle-map.md row names it); "
                        f"cite another capability as `{STEWARD_SPEC} CAP-{citation.number}`"
                    )
            else:
                finding = _qualifier_finding(where, citation, spec)
                if finding:
                    findings.append(finding)
    return findings


def help_strings(cli_source: str) -> dict[str, str]:
    """The ``_HELP`` mapping of ``cli.py``: duty -> its help text (the constant parts of an f-string joined)."""
    for node in ast.parse(cli_source).body:
        if isinstance(node, ast.Assign):
            targets, mapping = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, mapping = [node.target], node.value
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == "_HELP" for target in targets):
            assert isinstance(mapping, ast.Dict), "_HELP is not a dict literal"
            found: dict[str, str] = {}
            for key, value in zip(mapping.keys, mapping.values, strict=True):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    found[key.value] = "".join(
                        part.value
                        for part in ast.walk(value)
                        if isinstance(part, ast.Constant) and isinstance(part.value, str)
                    )
            return found
    raise AssertionError("cli.py has no module-level _HELP")


def help_findings(cli_source: str, spec: Spec) -> list[str]:
    """Every ``_HELP`` capability id that no ``contract.md`` row of that duty carries."""
    findings: list[str] = []
    for duty, text in help_strings(cli_source).items():
        carried = spec.duty_capabilities.get(duty, frozenset())
        for citation in citations(text):
            if spec.canonical(citation) not in carried:
                findings.append(
                    f"_HELP[{duty!r}] cites `{citation.text()}`, which no contract.md row of `steward {duty}` carries "
                    f"({sorted(carried) or 'none'})"
                )
    return findings


def families_for(module: str) -> tuple[str, ...]:
    """The absorbed Specs a module's lines may be re-keyed from (``module`` relative to the package root)."""
    return tuple(
        name for pattern, names in MODULE_FAMILIES.items() if fnmatch.fnmatchcase(module, pattern) for name in names
    )


@dataclass(frozen=True)
class Hunk:
    path: str
    old: tuple[str, ...]
    new: tuple[str, ...]


def hunks(diff_text: str) -> list[Hunk]:
    """The hunks of a ``git diff -U0``: each file's removed and added lines, per hunk."""
    found: list[Hunk] = []
    path: str | None = None
    in_hunk = False
    old: list[str] = []
    new: list[str] = []

    def close() -> None:
        if path is not None and (old or new):
            found.append(Hunk(path, tuple(old), tuple(new)))

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            close()
            path, in_hunk, old, new = None, False, [], []
        elif not in_hunk and line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif _HUNK.match(line):
            close()
            in_hunk, old, new = True, [], []
        elif in_hunk and line.startswith("-"):
            old.append(line[1:])
        elif in_hunk and line.startswith("+"):
            new.append(line[1:])
    close()
    return found


def rekey_pairs(hunk: Hunk) -> list[tuple[str, str]]:
    """The (old, new) line pairs of a hunk: lines whose text is unchanged once every citation is masked, and,
    between those, a run of rewritten lines that keeps its line count, paired in order."""
    masked_old = [mask(line) for line in hunk.old]
    masked_new = [mask(line) for line in hunk.new]
    pairs: list[tuple[str, str]] = []
    matcher = difflib.SequenceMatcher(None, masked_old, masked_new, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
            pairs.extend(zip(hunk.old[i1:i2], hunk.new[j1:j2], strict=True))
    return pairs


def rekey_fault(old: Citation, new: Citation, spec: Spec, module: str) -> str | None:
    """Why rewriting ``old`` as ``new`` is off the Spec's provenance map within ``module``'s family, or None when it
    holds. A bare id qualified, same number, with another Spec is not a re-key: the qualified id is judged where it
    stands (the live-Spec rule)."""
    if spec.canonical(old) == spec.canonical(new):
        return None
    pair = f"({old.text()}, {new.text()})"
    if not new.steward:
        if old.spec is None and old.prefix is None and old.number == new.number:
            return None
        return f"{pair} re-keys to another Spec's id, not through steward's map"
    absorbed, number = spec.provenance.get(new.number, ("", -1))
    if number != old.number or (old.spec not in (None, absorbed)):
        held = f"{absorbed} CAP-{number}" if absorbed else "no absorbed id"
        return f"{pair} is not on the map (CAP-{new.number} <- {held})"
    if absorbed not in families_for(module):
        return f"{pair} draws on {absorbed}, which is not in {module}'s family list"
    return None


def collapses(old_ids: list[Citation], new_ids: list[Citation], spec: Spec, module: str) -> bool:
    """True when each new id stands for a run of one or more adjacent old ids that all re-key to it (an absorbed
    id written beside its new id, ``spec-<absorbed> CAP-old / spec-pyforge-steward CAP-new``, kept once)."""
    if not new_ids or len(old_ids) <= len(new_ids):
        return False
    index = 0
    for position, new in enumerate(new_ids):
        if index >= len(old_ids) or rekey_fault(old_ids[index], new, spec, module) is not None:
            return False
        index += 1
        still_needed = len(new_ids) - position - 1
        while index < len(old_ids) - still_needed and rekey_fault(old_ids[index], new, spec, module) is None:
            index += 1
    return index == len(old_ids)


def rekey_findings(diff_text: str, spec: Spec, package: str = STEWARD_PACKAGE) -> list[str]:
    """Every re-key on a changed line that the Spec's provenance map, within the module's family, does not hold."""
    findings: list[str] = []
    for hunk in hunks(diff_text):
        if not hunk.path.startswith(package + "/"):
            continue
        module = hunk.path.removeprefix(package + "/")
        for old_line, new_line in rekey_pairs(hunk):
            old_ids, new_ids = citations(old_line), citations(new_line)
            if [spec.canonical(c) for c in old_ids] == [spec.canonical(c) for c in new_ids]:
                continue
            where = f"{module}: `{old_line.strip()}` -> `{new_line.strip()}`"
            if len(old_ids) != len(new_ids):
                if not collapses(old_ids, new_ids, spec, module):
                    findings.append(f"{where}: the line cites {len(old_ids)} id(s) before and {len(new_ids)} after")
                continue
            for old, new in zip(old_ids, new_ids, strict=True):
                fault = rekey_fault(old, new, spec, module)
                if fault:
                    findings.append(f"{where}: {fault}")
    return findings


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=_repo_root(), capture_output=True, text=True, check=False)


def branch_diff() -> str:
    """``git diff -U0`` from the branch's base on ``origin/main`` to the working tree, under the steward package;
    skips loudly when ``origin/main`` is not in this checkout."""
    if _git("rev-parse", "--verify", "--quiet", f"{ORIGIN_MAIN}^{{commit}}").returncode != 0:
        pytest.skip(f"{ORIGIN_MAIN} is not available in this checkout; the re-key guard needs the base ref")
    base = _git("merge-base", ORIGIN_MAIN, "HEAD")
    assert base.returncode == 0, base.stderr
    diff = _git("diff", "-U0", "--no-color", "--no-ext-diff", base.stdout.strip(), "--", STEWARD_PACKAGE)
    assert diff.returncode == 0, diff.stderr
    return diff.stdout


def source_modules() -> dict[str, str]:
    """Every steward source module, relative to the source root -> its text."""
    root = _repo_root() / SOURCE_ROOT
    return {path.relative_to(root).as_posix(): path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.py"))}


def package_modules() -> dict[str, str]:
    """Every ``.py`` under the steward package's ``src`` and ``tests``, relative to the package root -> its text."""
    root = _repo_root() / STEWARD_PACKAGE
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for top in ("src", "tests")
        for path in sorted((root / top).rglob("*.py"))
    }


def _report(what: str, findings: list[str]) -> str:
    return f"{what}:\n  " + "\n  ".join(findings)


# --------------------------------------------------------------------------- the live tree


def test_the_inputs_are_read_not_empty() -> None:
    spec = live_spec()
    assert len(spec.defined) >= 180
    assert spec.provenance[13] == ("spec-bmad-method-core-upgrade", 5)
    assert spec.allowed_for("cli.py") and spec.allowed_for("dashboard/audit.py")
    assert spec.allowed_for_path("src/pyforge/steward/upgrade.py") == spec.allowed_for("upgrade.py")
    assert spec.allowed_for_path("tests/unit/test_upgrade_pin_fan_out.py") == frozenset({12})
    assert {"canopy", "pap", "fnd"} <= spec.prefixes
    assert spec.aliases.get("fnd") == "spec-python-foundry-cutover"
    assert {"deploy", "upgrade", "suite", "track", "guards"} <= set(spec.duty_capabilities)


def test_string_constants_cite_defined_ids_in_their_modules_allowed_set() -> None:
    spec = live_spec()
    findings = [
        finding for module, source in source_modules().items() for finding in citation_findings(module, source, spec)
    ]
    assert not findings, _report("steward string constants cite ids that are not today's", findings)


def test_comments_and_docstrings_cite_todays_ids() -> None:
    spec = live_spec()
    modules = package_modules()
    assert any(path.startswith("src/") for path in modules) and any(path.startswith("tests/") for path in modules)
    findings = [finding for path, source in modules.items() for finding in comment_findings(path, source, spec)]
    assert not findings, _report("steward comments and docstrings cite ids that are not today's", findings)


def test_help_strings_cite_only_their_duty_capabilities() -> None:
    findings = help_findings(_read(f"{SOURCE_ROOT}/cli.py"), live_spec())
    assert not findings, _report("steward --help cites capabilities its duties do not carry", findings)


def test_module_families_are_absorbed_specs_and_match_files() -> None:
    spec = live_spec()
    absorbed = {name for name, _ in spec.provenance.values()}
    package = _repo_root() / STEWARD_PACKAGE
    files = [path.relative_to(package).as_posix() for path in package.rglob("*") if path.is_file()]
    for pattern, names in MODULE_FAMILIES.items():
        assert any(fnmatch.fnmatchcase(path, pattern) for path in files), f"{pattern} matches no steward module"
        missing = [name for name in names if name not in absorbed]
        assert not missing, f"{pattern}: {missing} is on no SPEC.md provenance line"


def test_rekey_pairs_follow_the_provenance_map() -> None:
    findings = rekey_findings(branch_diff(), live_spec())
    assert not findings, _report("a changed steward line re-keys an id off the Spec's provenance map", findings)


# --------------------------------------------------------------------------- the checker fires


def test_fires_on_an_undefined_id() -> None:
    findings = citation_findings("suite.py", 'X = "see CAP-9999 for the rest"\n', live_spec())
    assert findings == ["suite.py:1: `CAP-9999` is not an id SPEC.md defines"]


def test_fires_on_an_id_outside_the_modules_allowed_set() -> None:
    findings = citation_findings("suite.py", 'X = "pin-fan-out report (CAP-4 report-only)"\n', live_spec())
    assert findings == ["suite.py:1: `CAP-4` is not in suite.py's allowed set (no oracle-map.md row names it)"]


def test_fires_on_a_qualifier_that_names_no_live_spec_or_listed_prefix() -> None:
    source = 'X = "(Story 53.3 / hub:CAP-3)"\nY = "(Story 61.4, spec-work-passports-dated-extracts CAP-4)"\n'
    findings = citation_findings("track.py", source, live_spec())
    assert findings == [
        "track.py:1: `hub:CAP-3`: the prefix `hub:` is neither in CHAIN-STANDARD.md nor declared",
        "track.py:2: `spec-work-passports-dated-extracts CAP-4` names no live Spec",
    ]


def test_fires_on_a_comment_citing_an_id_outside_the_modules_allowed_set() -> None:
    source = 'X = "pin fan-out"  # pin-fan-out report (CAP-4 report-only)\n# the qualified form: spec-pyforge-steward CAP-12\n'
    findings = comment_findings("src/pyforge/steward/suite.py", source, live_spec())
    assert len(findings) == 1 and findings[0].startswith("src/pyforge/steward/suite.py:1: `CAP-4` is not in"), findings


def test_fires_on_a_docstring_citing_an_undefined_id_a_dead_spec_or_an_unlisted_prefix() -> None:
    source = '"""See CAP-9999.\n\n(Story 61.4, spec-work-passports-dated-extracts CAP-4; Story 53.3 / hub:CAP-3)."""\n'
    findings = comment_findings("src/pyforge/steward/track.py", source, live_spec())
    assert findings == [
        "src/pyforge/steward/track.py:1: `CAP-9999` is not an id SPEC.md defines",
        "src/pyforge/steward/track.py:3: `spec-work-passports-dated-extracts CAP-4` names no live Spec",
        "src/pyforge/steward/track.py:3: `hub:CAP-3`: the prefix `hub:` is neither in CHAIN-STANDARD.md nor declared",
    ]


def test_fires_on_a_test_docstring_citing_a_capability_the_test_does_not_prove() -> None:
    spec = live_spec()
    path = "tests/unit/test_upgrade_pin_fan_out.py"
    assert comment_findings(path, '"""Story 14.4 — CAP-12: pin fan-out."""\n', spec) == []
    assert comment_findings(path, '"""Range: spec-pyforge-steward CAP-9..CAP-13."""\n', spec) == []
    findings = comment_findings(path, '"""Story 14.4 — CAP-4: pin fan-out."""\n', spec)
    assert len(findings) == 1 and findings[0].startswith(f"{path}:1: `CAP-4` is not in {path}'s allowed set"), findings


def test_rekey_pairs_accept_a_qualification_and_a_collapsed_pair_but_not_a_wrong_one() -> None:
    def diff(module: str, old: str, new: str) -> str:
        path = f"{STEWARD_PACKAGE}/{module}"
        return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-{old}\n+{new}\n"

    spec = live_spec()
    held = diff(
        "src/pyforge/steward/keys.py", "    (Story 14.2, CAP-2 --", "    (Story 14.2, spec-pyforge-core CAP-2 --"
    ) + diff(
        "src/pyforge/steward/passport.py",
        "spec-work-passports-dated-extracts CAP-2 / spec-pyforge-steward CAP-140).",
        "spec-pyforge-steward CAP-140).",
    )
    assert rekey_findings(held, spec) == []
    wrong = diff(
        "src/pyforge/steward/keys.py", "    (Story 14.2, CAP-2 --", "    (Story 14.2, spec-pyforge-core CAP-3 --"
    )
    wrong += diff("src/pyforge/steward/upgrade.py", "# CAP-4 / CAP-5 report", "# CAP-13 report")
    findings = rekey_findings(wrong, spec)
    assert len(findings) == 2, findings
    assert "re-keys to another Spec's id, not through steward's map" in findings[0]
    assert "the line cites 2 id(s) before and 1 after" in findings[1]


def test_fires_on_a_help_string_citing_a_capability_its_duty_lacks() -> None:
    planted = '_HELP = {"track": "assemble one track.json (Story 53.4 / CAP-55)", "guards": "catalog (CAP-55)"}\n'
    findings = help_findings(planted, live_spec())
    assert len(findings) == 1 and findings[0].startswith("_HELP['track'] cites `CAP-55`"), findings


def test_rekey_pairs_fires_on_a_wrong_sibling_and_a_foreign_family() -> None:
    diff = (
        f"diff --git a/{SOURCE_ROOT}/upgrade.py b/{SOURCE_ROOT}/upgrade.py\n"
        f"--- a/{SOURCE_ROOT}/upgrade.py\n+++ b/{SOURCE_ROOT}/upgrade.py\n"
        "@@ -1,2 +1,2 @@\n"
        '-    "steward upgrade pin-fan-out — CAP-4 report-only",\n'
        '-    "steward upgrade prove-landed — CAP-5 post-apply verification",\n'
        '+    "steward upgrade pin-fan-out — CAP-13 report-only",\n'
        '+    "steward upgrade prove-landed — CAP-13 post-apply verification",\n'
        f"diff --git a/{SOURCE_ROOT}/suite.py b/{SOURCE_ROOT}/suite.py\n"
        f"--- a/{SOURCE_ROOT}/suite.py\n+++ b/{SOURCE_ROOT}/suite.py\n"
        "@@ -9 +9 @@\n"
        '-    "pin-fan-out (CAP-4 report-only)",\n'
        '+    "pin-fan-out (CAP-12 report-only)",\n'
    )
    findings = rekey_findings(diff, live_spec())
    assert len(findings) == 2, findings
    assert "(CAP-4, CAP-13) is not on the map (CAP-13 <- spec-bmad-method-core-upgrade CAP-5)" in findings[0]
    assert (
        "draws on spec-bmad-method-core-upgrade, which is not in src/pyforge/steward/suite.py's family" in findings[1]
    )
