"""Story 19.1 — station-owned gates for SKF skill + CAP-16 persona."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from pyforge.testing_kit import (
    changed_paths_since,
    pyforge_import_offenders,
    unsanctioned_commits,
)

STATION = "atlas"
SKILL_NAME = f"pyforge-{STATION}"
PERSONA = f"bmad-agent-{STATION}"
CONTENT_SKILL_MD = f".claude/skills/{SKILL_NAME}/active/{SKILL_NAME}/SKILL.md"
ALLOWED_KINDS = frozenset({"consult_content_skill", "grammar", "mcp"})
FREELANCE_KINDS = frozenset({"filesystem", "fs", "http", "adhoc_http"})
MCP_PATH = f"/stations/{STATION}/mcp"
GOLDEN = "atlas-version-e2e.json"


class PersonaContractError(AssertionError):
    """Transcript or skill violates CAP-16."""


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (
            (candidate / "pixi.toml").is_file()
            and (candidate / ".claude" / "skills" / "conda-forge-expert").is_dir()
            and (candidate / "src" / "shared" / "packages").is_dir()
        ):
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _skill_package(root: Path) -> Path:
    active = (root / ".claude" / "skills" / SKILL_NAME / "active").resolve()
    return active / SKILL_NAME


def _persona_dir(root: Path) -> Path:
    return root / ".claude" / "skills" / PERSONA


def _section(text: str, heading: str) -> str:
    pattern = rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text)
    return match.group(1) if match else ""


def validate_transcript(events: list[dict]) -> None:
    if not events:
        raise PersonaContractError("empty transcript")
    saw_surface = False
    for event in events:
        kind = event.get("kind")
        if kind in FREELANCE_KINDS:
            raise PersonaContractError(f"freelance {kind}")
        if kind not in ALLOWED_KINDS:
            raise PersonaContractError(f"disallowed kind {kind!r}")
        if kind == "consult_content_skill":
            if event.get("skill") != SKILL_NAME:
                raise PersonaContractError("consult must name the CAP-15 content skill")
            path = str(event.get("path") or "").replace("\\", "/")
            if CONTENT_SKILL_MD not in path and not path.endswith(f"{SKILL_NAME}/SKILL.md"):
                raise PersonaContractError("consult path must be the CAP-15 SKILL.md")
        elif kind == "grammar":
            argv = event.get("argv") or []
            if len(argv) < 3 or argv[0] != "pyforge" or argv[1] != STATION:
                raise PersonaContractError("grammar must be pyforge atlas …")
            saw_surface = True
        elif kind == "mcp":
            if event.get("method") != "POST":
                raise PersonaContractError("mcp must be POST")
            if event.get("path") != MCP_PATH:
                raise PersonaContractError(f"mcp path must be {MCP_PATH}")
            saw_surface = True
    if not saw_surface:
        raise PersonaContractError("station task must use FR-13 grammar or FR-11 MCP")


def assert_skill_forbids_freelance(text: str) -> None:
    allowed = _section(text, "Allowed actions (CAP-16)")
    forbidden = _section(text, "Forbidden actions")
    if not allowed.strip():
        raise PersonaContractError("persona skill missing Allowed actions (CAP-16)")
    if not forbidden.strip():
        raise PersonaContractError("persona skill missing Forbidden actions")
    if re.search(r"(?i)\b(read|write|delete|strreplace)\b tool", allowed):
        raise PersonaContractError("persona is allowed to use filesystem tools")
    if re.search(r"(?i)\b(curl|requests|httpx|webfetch|websearch|urllib)\b", allowed):
        raise PersonaContractError("persona is allowed to use ad-hoc HTTP")
    if re.search(r"(?i)direct filesystem", allowed) and "no direct" not in allowed.lower():
        raise PersonaContractError("persona is allowed to use filesystem")
    if not re.search(r"(?i)no direct filesystem", forbidden):
        raise PersonaContractError("persona skill does not forbid direct filesystem")
    if not re.search(r"(?i)no ad-hoc HTTP", forbidden):
        raise PersonaContractError("persona skill does not forbid ad-hoc HTTP")


def test_skf_compile_path_is_present():
    root = _repo_root()
    required = [
        root / "_bmad" / "skf" / "skf-create-skill" / "SKILL.md",
        root / ".claude" / "skills" / "skf-create-skill" / "SKILL.md",
        root / ".claude" / "skills" / "shared" / "scripts" / "skf-extract-public-api.py",
        root / ".claude" / "skills" / "shared" / "scripts" / "skf-validate-frontmatter.py",
        root / ".claude" / "skills" / "shared" / "scripts" / "skf-validate-output.py",
    ]
    missing = [str(p.relative_to(root)) for p in required if not p.is_file()]
    assert not missing, f"SKF compile path removed: {missing}"


def test_compiled_skill_exists_with_active_pointer_and_provenance():
    root = _repo_root()
    pkg = _skill_package(root)
    assert pkg.is_dir()
    skill_md = pkg / "SKILL.md"
    provenance = json.loads((pkg / "provenance-map.json").read_text(encoding="utf-8"))
    meta = json.loads((pkg / "metadata.json").read_text(encoding="utf-8"))

    assert meta["generated_by"] == "create-skill"
    assert meta["name"] == SKILL_NAME
    assert meta["source_repo"].endswith(f"pyforge-{STATION}")
    assert provenance["source_commit"]
    assert provenance["entries"], "provenance-map.json must pin at least one export"
    for entry in provenance["entries"]:
        src = entry["source_file"]
        assert "pyforge-atlas" in src
        line = int(entry["source_line"])
        path = root / src
        assert path.is_file(), src
        assert line >= 1
        text = path.read_text(encoding="utf-8").splitlines()
        assert line <= len(text), f"{src}:{line} out of range"

    brief = root / ".claude" / "skills" / SKILL_NAME / "skill-brief.yaml"
    assert brief.is_file()
    assert "src/shared/packages/pyforge-atlas" in brief.read_text(encoding="utf-8")

    active = root / ".claude" / "skills" / SKILL_NAME / "active"
    assert active.is_symlink()
    assert (active / SKILL_NAME / "SKILL.md").is_file()

    body = skill_md.read_text(encoding="utf-8")
    assert "pyforge atlas" in body
    assert "conda-forge-expert" in body
    assert "cf-atlas-legacy" in body


def test_skf_validators_pass_on_compiled_package():
    root = _repo_root()
    pkg = _skill_package(root)
    skill_md = pkg / "SKILL.md"
    fm = subprocess.run(
        [
            sys.executable,
            str(root / ".claude" / "skills" / "shared" / "scripts" / "skf-validate-frontmatter.py"),
            str(skill_md),
            "--skill-dir-name",
            SKILL_NAME,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert fm.returncode == 0, fm.stdout + fm.stderr
    fm_payload = json.loads(fm.stdout)
    assert fm_payload["status"] in {"pass", "warn"}
    assert fm_payload["summary"]["high"] == 0

    out = subprocess.run(
        [
            sys.executable,
            str(root / ".claude" / "skills" / "shared" / "scripts" / "skf-validate-output.py"),
            str(pkg),
            "--generated-by",
            "create-skill",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(out.stdout)
    high = payload["summary"]["by_severity"]["high"]
    assert high == 0, payload


def test_context_files_unchanged():
    root = _repo_root()
    for name in ("CLAUDE.md", "AGENTS.md"):
        # skf-export-skill (3d745c2c31, 2026-08-26) made the SKF:BEGIN/END managed
        # section the legitimate, tool-generated content of these files — a flat
        # ban on the marker is stale. The invariant is "not hand-edited", checked
        # via the exporter's own well-formedness gate, not marker absence.
        result = json.loads(
            subprocess.check_output(
                [
                    sys.executable,
                    str(root / ".claude" / "skills" / "shared" / "scripts" / "skf-rebuild-managed-sections.py"),
                    str(root / name),
                    "check",
                ],
                text=True,
            )
        )
        if result["has_managed_section"]:
            assert result["markers_valid"], f"{name}: malformed SKF managed section"
        # A second managed marker, `bmad:context`, is the sanctioned surface for
        # content moved by `bmad-project-context adopt`/`audit` (Story 30.2,
        # 2026-09-06, D1). A well-formed bmad:context block is legitimate,
        # tool-mediated content the same way an SKF managed section is; the
        # unconditional "must stay unchanged" assertion this test used to carry
        # is retired in favor of checking both markers stay well-formed,
        # matching the docstring's own stated invariant ("not hand-edited", not
        # "never touched").
        if name == "AGENTS.md":
            text = (root / name).read_text(encoding="utf-8")
            opens = text.count("<!-- bmad:context -->")
            closes = text.count("<!-- /bmad:context -->")
            assert opens == closes, f"{name}: unbalanced bmad:context markers"
            assert opens <= 1, f"{name}: more than one bmad:context block"


_CFE_SURFACE = ".claude/skills/conda-forge-expert"
_CFE_CHANGELOG = f"{_CFE_SURFACE}/CHANGELOG.md"


def test_conda_forge_expert_not_replaced():
    root = _repo_root()
    cfe = root / ".claude" / "skills" / "conda-forge-expert"
    assert (cfe / "SKILL.md").is_file()
    assert not (cfe / "metadata.json").exists()
    assert not (cfe / "active").exists()
    # Sanctioned Rule-2 retro -- subject starts `retro:` AND the CFE CHANGELOG
    # moves in the same commit, the fleet rule
    # `scripts/mason_cfe_surface_check.py` enforces for mason. A station story
    # never touches the surface; a fleet hygiene branch may carry the one
    # sanctioned retro (2026-09-04, PR #1043).
    unsanctioned = unsanctioned_commits(root, pathspec=_CFE_SURFACE, changelog_path=_CFE_CHANGELOG)
    assert not unsanctioned, (
        "conda-forge-expert changed vs origin/main outside a sanctioned `retro:` "
        f"commit that moves its CHANGELOG: {unsanctioned}"
    )


def test_does_not_replace_cf_atlas_legacy():
    root = _repo_root()
    assert (root / ".claude" / "skills" / "cf-atlas-legacy").is_dir()
    assert SKILL_NAME != "cf-atlas-legacy"


def test_golden_transcript_is_grammar_and_mcp_only():
    root = _repo_root()
    path = _persona_dir(root) / "transcripts" / GOLDEN
    events = json.loads(path.read_text(encoding="utf-8"))
    validate_transcript(events)
    kinds = {event["kind"] for event in events}
    assert "consult_content_skill" in kinds
    assert "grammar" in kinds
    assert "mcp" in kinds
    assert kinds <= ALLOWED_KINDS


def test_freelance_filesystem_in_transcript_fails():
    root = _repo_root()
    events = json.loads((_persona_dir(root) / "transcripts" / GOLDEN).read_text(encoding="utf-8"))
    events.append({"kind": "filesystem", "path": "src/shared/packages/pyforge-atlas/README.md"})
    try:
        validate_transcript(events)
    except PersonaContractError as exc:
        assert "freelance" in str(exc)
        return
    raise AssertionError("filesystem freelance was permitted")


def test_adhoc_http_in_transcript_fails():
    root = _repo_root()
    events = json.loads((_persona_dir(root) / "transcripts" / GOLDEN).read_text(encoding="utf-8"))
    events.append({"kind": "http", "method": "GET", "url": "https://example.com"})
    try:
        validate_transcript(events)
    except PersonaContractError as exc:
        assert "freelance" in str(exc)
        return
    raise AssertionError("ad-hoc HTTP freelance was permitted")


def test_station_binary_without_pyforge_grammar_fails():
    events = [
        {
            "kind": "consult_content_skill",
            "skill": SKILL_NAME,
            "path": CONTENT_SKILL_MD,
        },
        {"kind": "grammar", "argv": ["pyforge-atlas", "--version"]},
    ]
    try:
        validate_transcript(events)
    except PersonaContractError:
        return
    raise AssertionError("bare pyforge-atlas binary was accepted as FR-13 grammar")


def test_mcp_get_is_not_the_service_face():
    events = [
        {
            "kind": "consult_content_skill",
            "skill": SKILL_NAME,
            "path": CONTENT_SKILL_MD,
        },
        {"kind": "mcp", "method": "GET", "path": MCP_PATH},
    ]
    try:
        validate_transcript(events)
    except PersonaContractError:
        return
    raise AssertionError("GET MCP was accepted as FR-11")


def test_mcp_other_station_is_not_atlas_face():
    events = [
        {
            "kind": "consult_content_skill",
            "skill": SKILL_NAME,
            "path": CONTENT_SKILL_MD,
        },
        {"kind": "mcp", "method": "POST", "path": "/stations/scribe/mcp"},
    ]
    try:
        validate_transcript(events)
    except PersonaContractError:
        return
    raise AssertionError("scribe MCP was accepted as the atlas face")


def test_live_persona_skill_forbids_filesystem_and_adhoc_http():
    root = _repo_root()
    skill = (_persona_dir(root) / "SKILL.md").read_text(encoding="utf-8")
    assert_skill_forbids_freelance(skill)
    assert SKILL_NAME in skill
    assert "pyforge atlas" in skill
    assert MCP_PATH in skill
    assert "_bmad/scripts/resolve_customization.py" in skill


def test_permissive_skill_text_fails_contract():
    live = (_persona_dir(_repo_root()) / "SKILL.md").read_text(encoding="utf-8")
    allowed = "## Allowed actions (CAP-16)\n\n- You may use the Read tool and curl https://example.com\n"
    forbidden = "## Forbidden actions\n\nNothing.\n"
    permissive = re.sub(
        r"(?ms)^## Allowed actions \(CAP-16\).*?(?=^## Forbidden actions)",
        allowed,
        live,
    )
    permissive = re.sub(
        r"(?ms)^## Forbidden actions.*",
        forbidden,
        permissive,
    )
    try:
        assert_skill_forbids_freelance(permissive)
    except PersonaContractError:
        return
    raise AssertionError("permissive persona skill was accepted")


def test_persona_is_bmad_launcher_not_skf_compiled():
    root = _repo_root()
    persona = _persona_dir(root)
    assert (persona / "SKILL.md").is_file()
    assert (persona / "customize.toml").is_file()
    assert not (persona / "metadata.json").exists()
    assert not (persona / "provenance-map.json").exists()
    assert not (persona / "active").exists()
    customize = (persona / "customize.toml").read_text(encoding="utf-8")
    assert CONTENT_SKILL_MD in customize
    assert "pyforge atlas" in customize
    assert MCP_PATH in customize
    assert "bmad-build" not in customize


def test_story_does_not_add_pyforge_under_src_platform():
    root = _repo_root()
    changed = changed_paths_since(root, pathspec="src/platform")
    offenders = pyforge_import_offenders(changed, root)
    assert not offenders, f"src/platform pyforge imports in this diff: {changed} {offenders}"
