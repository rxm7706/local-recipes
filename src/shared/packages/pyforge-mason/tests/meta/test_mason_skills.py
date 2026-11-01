"""Story 19.2+ — hand-authored Mason craft and campaign skills.

Story 19.6 (spec-pyforge-mason CAP-29, EGM audit MAS-M-Z4/MAS-M-D5) widens the
"no Mason skill restates a CFE gotcha" check from one heading regex over four
``SKILL.md`` files to every ``*.md`` in the Mason skill tier (the four
hand-authored skills, their ``references/``, and the SKF-compiled station
skill): no gotcha heading, no copied CFE fix sentence, and no cited G-id that
CFE does not define. A G-id cited with a one-line gist is a pointer and passes.
It also pins that each campaign how-to and its archived stub link their skill.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest
import yaml

CFE_LINK_FRAGMENT = ".claude/skills/conda-forge-expert/"
GOTCHA_HEADING_RE = re.compile(r"^### G\d+\.", re.MULTILINE)

# Story 19.6: the whole Mason skill tier, every *.md under each directory.
MASON_SKILL_DIRS: tuple[str, ...] = (
    ".claude/skills/mason-package",
    ".claude/skills/mason-environment",
    ".claude/skills/mason-feedstock-platform-expansion",
    ".claude/skills/mason-feedstock-failure-remediation",
    ".claude/skills/pyforge-mason/active/pyforge-mason",
)
CFE_SKILL_MD = ".claude/skills/conda-forge-expert/SKILL.md"
# A gotcha heading at any level; a letter suffix (G8b) is its own id, never G8.
ANY_GOTCHA_HEADING_RE = re.compile(r"^#{1,6} (G\d+[a-z]?)\.", re.MULTILINE)
CFE_GOTCHA_DEFINITION_RE = re.compile(r"^### (G\d+[a-z]?)\.", re.MULTILINE)
GOTCHA_ID_RE = re.compile(r"\bG\d+[a-z]?\b")
# "G31–G34" cites G32 and G33 too.
GOTCHA_RANGE_RE = re.compile(r"\bG(\d+)\s*[–—-]\s*G(\d+)\b")
CFE_FIX_RE = re.compile(r"\*\*Fix[^*\n]*\*\*:?(.*?)(?=\n\n\*\*|\n#{2,3} |\Z)", re.DOTALL)
FENCED_CODE_RE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
# Shorter fix sentences ("Quote the version.") are a gist, not a copy.
MIN_COPIED_SENTENCE_CHARS = 60

# Story 19.6: each campaign how-to and its archived stub point at their skill.
CAMPAIGN_POINTERS: dict[str, str] = {
    "docs/how-to/feedstock-platform-expansion.md": "mason-feedstock-platform-expansion",
    "docs/how-to/feedstock-failure-remediation.md": "mason-feedstock-failure-remediation",
    "archive/docs/specs/feedstock-platform-expansion.md": "mason-feedstock-platform-expansion",
    "archive/docs/specs/feedstock-failure-remediation.md": "mason-feedstock-failure-remediation",
}

MASON_HAND_AUTHORED_SKILLS: tuple[dict[str, object], ...] = (
    {
        "skill_dir": "mason-package",
        "expected_name": "mason-package",
        "required_phrases": (
            "pyforge mason package build",
            "pyforge mason package ship",
            "pypi-test",
            "pypi",
            "conda-forge",
            "channel:",
            "--yes",
        ),
        "gate_phrases": (
            "pypi-test",
            "pypi",
            "gate",
        ),
    },
    {
        "skill_dir": "mason-environment",
        "expected_name": "mason-environment",
        "required_phrases": (
            "pyforge mason environment lock",
            "pyforge mason environment check",
            "discover",
            "explicit",
            "--platform",
            "engine_name",
            "engine_version",
            "conda-lock",
        ),
    },
    {
        "skill_dir": "mason-feedstock-platform-expansion",
        "expected_name": "mason-feedstock-platform-expansion",
        "required_phrases": (
            "target_platforms",
            "conda-forge-expert/guides/feedstock-platform-expansion.md",
            "Worked Examples",
            "references/worked-examples.md",
        ),
    },
    {
        "skill_dir": "mason-feedstock-failure-remediation",
        "expected_name": "mason-feedstock-failure-remediation",
        "required_phrases": (
            "FLAKE",
            "REAL_FIX",
            "BLOCKED",
            "Wave A",
            "Wave E",
            "references/worked-examples.md",
        ),
    },
)


class MasonSkillContractError(AssertionError):
    """A hand-authored Mason skill violates the Story 19.2 contract."""


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise MasonSkillContractError("could not locate repo root (pixi.toml + .claude/skills)")


def _parse_skill_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        raise MasonSkillContractError("SKILL.md must start with YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise MasonSkillContractError("SKILL.md frontmatter not closed")
    data = yaml.safe_load(parts[1])
    if not isinstance(data, dict):
        raise MasonSkillContractError("SKILL.md frontmatter must be a mapping")
    return {str(k): str(v) if v is not None else "" for k, v in data.items()}


def _validate_skill_file(skill_md: Path, spec: dict[str, object]) -> None:
    if not skill_md.is_file():
        raise MasonSkillContractError(f"missing {skill_md.relative_to(_repo_root())}")
    text = skill_md.read_text(encoding="utf-8")
    frontmatter = _parse_skill_frontmatter(text)
    expected_name = str(spec["expected_name"])
    if frontmatter.get("name") != expected_name:
        raise MasonSkillContractError(
            f"{skill_md}: frontmatter name: expected {expected_name!r}, got {frontmatter.get('name')!r}"
        )
    if not frontmatter.get("description", "").strip():
        raise MasonSkillContractError(f"{skill_md}: description: frontmatter must be non-empty")

    body = text.split("---", 2)[2]
    for phrase in spec["required_phrases"]:
        if phrase not in body:
            raise MasonSkillContractError(f"{skill_md}: body must mention {phrase!r}")

    for phrase in spec.get("gate_phrases", ()):
        if phrase not in body:
            raise MasonSkillContractError(f"{skill_md}: body must document pypi-test gate (missing {phrase!r})")

    if CFE_LINK_FRAGMENT not in text:
        raise MasonSkillContractError(f"{skill_md}: must link {CFE_LINK_FRAGMENT} (conda-forge target defers to CFE)")

    gotcha = GOTCHA_HEADING_RE.search(text)
    if gotcha:
        line_no = text[: gotcha.start()].count("\n") + 1
        raise MasonSkillContractError(
            f"{skill_md}:{line_no}: CFE gotcha heading {gotcha.group(0)!r} is forbidden "
            "(recipe knowledge stays in conda-forge-expert)"
        )


@pytest.mark.parametrize("spec", MASON_HAND_AUTHORED_SKILLS, ids=lambda s: str(s["skill_dir"]))
def test_hand_authored_mason_skill_contract(spec: dict[str, object]) -> None:
    root = _repo_root()
    skill_dir = str(spec["skill_dir"])
    skill_md = root / ".claude" / "skills" / skill_dir / "SKILL.md"
    _validate_skill_file(skill_md, spec)


def test_gotcha_heading_detector_is_not_vacuous() -> None:
    root = _repo_root()
    source = root / ".claude" / "skills" / "mason-package" / "SKILL.md"
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "SKILL.md"
        planted = source.read_text(encoding="utf-8") + "\n### G99. Planted gotcha for meta-test\n"
        copy.write_text(planted, encoding="utf-8")
        spec = MASON_HAND_AUTHORED_SKILLS[0]
        with pytest.raises(MasonSkillContractError, match="G99"):
            _validate_skill_file(copy, spec)


# --- Story 19.6: the whole skill tier, every G-id, every campaign pointer ---


def _display(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _line_of(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def _normalise(text: str) -> str:
    return " ".join(text.split())


def mason_skill_files(root: Path) -> list[Path]:
    """Every ``*.md`` under each Mason skill directory; a missing directory is a contract break."""
    files: list[Path] = []
    for rel in MASON_SKILL_DIRS:
        skill_dir = root / rel
        if not (skill_dir / "SKILL.md").is_file():
            raise MasonSkillContractError(f"missing {rel}/SKILL.md")
        files.extend(sorted(skill_dir.rglob("*.md")))
    return files


def cfe_gotcha_ids(cfe_text: str) -> frozenset[str]:
    """The G-ids CFE defines: one ``### G<n>.`` heading each."""
    return frozenset(CFE_GOTCHA_DEFINITION_RE.findall(cfe_text))


def cfe_fix_sentences(cfe_text: str) -> dict[str, tuple[str, ...]]:
    """Per CFE gotcha, the prose sentences of its ``**Fix**`` text long enough to be a copy, not a gist."""
    heads = list(CFE_GOTCHA_DEFINITION_RE.finditer(cfe_text))
    out: dict[str, tuple[str, ...]] = {}
    for i, head in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(cfe_text)
        section = cfe_text[head.start() : end]
        sentences: list[str] = []
        for fix in CFE_FIX_RE.finditer(section):
            prose = _normalise(FENCED_CODE_RE.sub(" ", fix.group(1)))
            sentences.extend(s for s in SENTENCE_SPLIT_RE.split(prose) if len(s) >= MIN_COPIED_SENTENCE_CHARS)
        if sentences:
            out[head.group(1)] = tuple(sentences)
    return out


def cited_gotcha_ids(text: str) -> dict[str, int]:
    """Each G-id the text cites (ranges expanded), mapped to the offset of its first citation."""
    cited: dict[str, int] = {}
    for match in GOTCHA_ID_RE.finditer(text):
        cited.setdefault(match.group(0), match.start())
    for match in GOTCHA_RANGE_RE.finditer(text):
        low, high = int(match.group(1)), int(match.group(2))
        for n in range(low, high + 1):
            cited.setdefault(f"G{n}", match.start())
    return cited


def skill_file_violations(
    path: Path,
    *,
    root: Path,
    defined: frozenset[str],
    fix_sentences: dict[str, tuple[str, ...]],
) -> list[str]:
    """CAP-29's restated-gotcha and dangling-G-id rules for one skill file."""
    text = path.read_text(encoding="utf-8")
    name = _display(path, root)
    violations = [
        f"{name}:{_line_of(text, m.start())}: CFE gotcha heading {m.group(0)!r} is forbidden "
        "(recipe knowledge stays in conda-forge-expert; cite the G-id with a one-line gist)"
        for m in ANY_GOTCHA_HEADING_RE.finditer(text)
    ]
    for gid, offset in sorted(cited_gotcha_ids(text).items(), key=lambda kv: kv[1]):
        if gid not in defined:
            violations.append(
                f"{name}:{_line_of(text, offset)}: cites {gid}, which has no '### {gid}.' heading in {CFE_SKILL_MD}"
            )
    flat = _normalise(text)
    for gid, sentences in fix_sentences.items():
        for sentence in sentences:
            if sentence in flat:
                violations.append(f"{name}: copies CFE {gid} fix text {sentence[:70]!r} (cite {gid} instead)")
    return violations


def pointer_violation(path: Path, skill: str) -> str | None:
    """A campaign how-to or archived stub that no longer links its skill's SKILL.md."""
    if not path.is_file():
        return f"{path}: missing (it must point at .claude/skills/{skill}/SKILL.md)"
    link = re.compile(rf"\[[^\]]*\.claude/skills/{re.escape(skill)}/SKILL\.md[^\]]*\]\(")
    if not link.search(path.read_text(encoding="utf-8")):
        return f"{path}: does not link .claude/skills/{skill}/SKILL.md"
    return None


def _cfe_text(root: Path) -> str:
    return (root / CFE_SKILL_MD).read_text(encoding="utf-8")


def test_every_mason_skill_file_restates_no_gotcha_and_cites_only_real_g_ids() -> None:
    root = _repo_root()
    cfe = _cfe_text(root)
    defined = cfe_gotcha_ids(cfe)
    assert defined, f"{CFE_SKILL_MD} defines no '### G<n>.' gotcha"
    fixes = cfe_fix_sentences(cfe)
    assert fixes, f"{CFE_SKILL_MD}: no **Fix** text extracted"
    files = mason_skill_files(root)
    scanned = {_display(f, root) for f in files}
    for rel in MASON_SKILL_DIRS:
        assert f"{_display(root / rel, root)}/SKILL.md" in scanned, rel
    assert any("/references/" in s for s in scanned), "references/*.md must be scanned"
    violations = [v for f in files for v in skill_file_violations(f, root=root, defined=defined, fix_sentences=fixes)]
    assert not violations, "\n".join(violations)


def test_skill_tier_scan_is_not_vacuous(tmp_path: Path) -> None:
    root = _repo_root()
    cfe = _cfe_text(root)
    defined = cfe_gotcha_ids(cfe)
    fixes = cfe_fix_sentences(cfe)
    assert "G95" in defined and "G999" not in defined
    refs = tmp_path / "references"
    refs.mkdir()

    def scan(body: str) -> list[str]:
        target = refs / "worked-examples.md"
        target.write_text(body, encoding="utf-8")
        return skill_file_violations(target, root=root, defined=defined, fix_sentences=fixes)

    heading = scan("# Worked examples\n\n### G95. Planted gotcha heading\n")
    assert len(heading) == 1 and "worked-examples.md:3:" in heading[0] and "G95" in heading[0], heading

    dangling = scan("# Worked examples\n\nPer CFE **G999**, see the skill.\n")
    assert len(dangling) == 1 and "G999" in dangling[0] and "worked-examples.md:3:" in dangling[0], dangling

    suffixed = scan("Per skill G8b: a letter suffix is its own id.\n")
    assert len(suffixed) == 1 and "G8b" in suffixed[0], suffixed

    ranged = cited_gotcha_ids("gotchas G31–G34")
    assert set(ranged) == {"G31", "G32", "G33", "G34"}, ranged

    copied_sentence = fixes["G85"][0]
    copied = scan(f"# Worked examples\n\n{copied_sentence}\n")
    assert len(copied) == 1 and "copies CFE G85 fix text" in copied[0], copied

    assert scan("- **G95** (BCTB block, see CFE) — a pointer with a one-line gist.\n") == []


@pytest.mark.parametrize(("rel", "skill"), sorted(CAMPAIGN_POINTERS.items()), ids=lambda v: str(v))
def test_campaign_how_to_and_stub_link_their_skill(rel: str, skill: str) -> None:
    violation = pointer_violation(_repo_root() / rel, skill)
    assert violation is None, violation


def test_campaign_pointer_check_is_not_vacuous(tmp_path: Path) -> None:
    root = _repo_root()
    rel, skill = next(iter(CAMPAIGN_POINTERS.items()))
    source = (root / rel).read_text(encoding="utf-8")
    stripped = "\n".join(line for line in source.splitlines() if f".claude/skills/{skill}/SKILL.md" not in line)
    planted = tmp_path / Path(rel).name
    planted.write_text(stripped, encoding="utf-8")
    violation = pointer_violation(planted, skill)
    assert violation is not None and Path(rel).name in violation and skill in violation, violation
