"""Story 46.1 / AD-2 & AD-6: the adoption register governs wiring.

`adoption-register.md` is authored and settled (this test verifies it, never
decides it -- see the story's own Boundaries & Constraints). Two invariants
are pinned here so the register cannot silently drift out from under the
live tree:

- AD-6 (status-cell hygiene): every § 1 "Status / story" cell stays a story
  key, never a bare lifecycle-status word (`done`, `blocked`, `backlog`,
  `in-progress`, `ready`) -- word-boundary matched so "unblocked" is not a
  false positive.
- AD-2 (routing home): for every § 2 skill whose dir currently exists on
  disk, `CLAUDE.md` never mentions it; and when the row names exactly one
  wielding station, that station's persona skill (`bmad-agent-<station>`)
  does mention it.

Live 2026-09-07 finding (recorded in this story's spec Code Map and
`.memlog.md`): as of Story 46.1, only `bmad-cis-*` (herald, scribe --
multi-station) and `skf-*` (all stations) were provisioned among § 2's rows,
so no real row exercised the single-station positive branch. That branch is
still real code, not dead code -- `test_single_station_branch_is_not_dead_code`
proves it against a synthetic fixture root, both the positive and negative
case.

Story 46.5 update: `release-please` (labs) is now provisioned AND routed
(`bmad-agent-steward`), so it is the first REAL row to exercise the
single-station positive branch. Its three sibling labs skills
(`mcp-builder`, `slides-generator`, `multi-repo-git-ops`) were provisioned by
the same story; `mcp-builder` has since been routed by atlas 24.1
(`bmad-agent-atlas`), `slides-generator` by herald 18.3
(`bmad-agent-herald`), and `multi-repo-git-ops` by marshal 31.6
(`bmad-agent-marshal`) -- all three siblings now routed, none remaining in
`_ROUTING_STORY_NOT_YET_LANDED` below;
`test_no_labs_skill_outside_the_consent_list_is_present` guards the
separate CAP-6 invariant that only the operator's four-name 2026-09-06
consent list ever lands under `.claude/skills/`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FORBIDDEN_STATUS_WORDS = re.compile(
    r"(?i)\b(?:done|blocked|backlog|in-progress|in-review|ready|draft|shipped|"
    r"complete|paused|superseded)\b"
)

REGISTER_RELATIVE = (
    "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md"
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _register_text(root: Path) -> str:
    return (root / REGISTER_RELATIVE).read_text(encoding="utf-8")


def _section(text: str, number: int) -> str:
    """Body of markdown section ``## <number>. ...`` up to the next ``## N.``."""
    pattern = rf"(?ms)^## {number}\.\s.*?\n(.*?)(?=^## \d+\.|\Z)"
    match = re.search(pattern, text)
    if not match:
        raise AssertionError(f"could not locate adoption-register.md section {number}")
    return match.group(1)


def _table_rows(section_text: str) -> list[list[str]]:
    """Markdown table rows (header included), the ``|---|---|`` rule dropped.

    Matches both bare-dash and colon-aligned separator rows (``:---``,
    ``:---:``, ``---:``) -- a colon-aligned separator would otherwise slip
    through as a spurious data row.
    """
    rows: list[list[str]] = []
    for line in section_text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        rows.append(cells)
    return rows


def _skill_names(cell: str) -> list[str]:
    """Backtick-quoted skill identifiers in a § 2 'Skill' cell."""
    return re.findall(r"`([^`]+)`", cell)


def _skill_dir_exists(skills_dir: Path, name: str) -> bool:
    """`name` may be an exact dir name or a `<prefix>-*` glob shape."""
    if name.endswith("-*"):
        prefix = name[:-1]
        return skills_dir.is_dir() and any(p.is_dir() and p.name.startswith(prefix) for p in skills_dir.iterdir())
    return (skills_dir / name).is_dir()


def _claude_md_search_term(name: str) -> str:
    """`bmad-cis-*` -> `bmad-cis-`; an exact name is used verbatim.

    Matches this story's own Verification command
    (``grep -c "bmad-cis\\|skf-" CLAUDE.md``), which greps the glob's prefix,
    not the literal glob string.
    """
    return name[:-1] if name.endswith("*") else name


def _station_shape(cell: str) -> tuple[str, str | None]:
    """Classify a § 2 'Wielding station' cell.

    ``("all", None)`` for the register's own `all stations` rows, ``("multi",
    None)`` for a cell naming more than one station -- comma-, slash-, or
    semicolon-joined (e.g. ``herald, scribe``, ``warden / marshal``,
    ``marshal (workflows, review lens); warden (advisory)``) -- else
    ``("single", <station>)`` with a trailing parenthetical annotation
    (``herald (studio only)``) stripped down to the leading station token.

    A bare parenthetical on an otherwise single station is not itself a
    multi-station marker (a comma *inside* one station's own parenthetical,
    as in ``marshal (workflows, review lens)`` alone, must not misclassify
    that station as multi) -- so the comma/slash/semicolon check runs on the
    cell with any parenthetical content removed first.
    """
    normalized = cell.strip()
    if normalized.lower() == "all stations":
        return ("all", None)
    stripped_of_parens = re.sub(r"\([^)]*\)", "", normalized)
    if any(sep in stripped_of_parens for sep in (",", "/", ";")):
        return ("multi", None)
    station = normalized.split("(")[0].strip()
    return ("single", station)


def _mention_re(name: str) -> re.Pattern[str]:
    """Word-boundary matcher for a skill name, honouring the glob-prefix form.

    Two defects this closes, both found by the 2026-09-08 deferred-work sweep and
    recorded as `pyforge-steward` DW-FU-46-1-2 / DW-FU-46-1-6 and `pyforge-atlas`
    DW-FU-24-1 (one helper, indicted from three ledger rows):

    * **Plain substring matching produced real false passes.** Verifying
      DW-FU-42-2-11 the sweep found `revoke` present twice in a persona card --
      both times as the CREDENTIAL duty (`steward keys {...,revoke}`), never the
      run duty being looked for. A substring test cannot tell those apart.
    * ``-`` must count as a word character here, or `bmad-os-changelog` matches
      inside `bmad-os-changelog-social` and a routing line for one skill would
      satisfy the check for its sibling.

    A glob name (`bmad-cis-*`) keeps its prefix semantics -- boundary required
    before the stem only, since the stem is deliberately open-ended.
    """
    term = _claude_md_search_term(name)
    tail = "" if name.endswith("*") else r"(?![\w-])"
    return re.compile(r"(?<![\w-])" + re.escape(term) + tail)


#: Files a persona skill may carry its routing text in. `SKILL.md` and
#: `customize.toml` were the original two; `reference/*.md` and `README.md` were
#: added 2026-09-08 (DW-FU-46-1-2) -- a persona that documented its routing in a
#: reference file read as un-routed to this check.
_PERSONA_ROUTING_FILES = ("SKILL.md", "customize.toml", "README.md")


def _persona_mentions(root: Path, station: str, name: str) -> bool:
    persona_dir = root / ".claude" / "skills" / f"bmad-agent-{station}"
    rx = _mention_re(name)
    candidates = [persona_dir / f for f in _PERSONA_ROUTING_FILES]
    candidates += sorted(persona_dir.glob("reference/*.md"))
    for path in candidates:
        if path.is_file() and rx.search(path.read_text(encoding="utf-8")):
            return True
    return False


def _claude_md_mentions(claude_md_text: str, name: str) -> bool:
    return bool(_mention_re(name).search(claude_md_text))


# ── § 1 status-cell hygiene (AD-6) ──────────────────────────────────────────


def test_status_story_cells_never_carry_a_bare_lifecycle_status_word():
    root = _repo_root()
    rows = _table_rows(_section(_register_text(root), 1))
    assert rows, "no § 1 table rows parsed at all -- table shape likely changed"
    header, data_rows = rows[0], rows[1:]
    assert header[-1] == "Status / story", f"§ 1 header shape changed: {header!r}"
    assert data_rows, "no § 1 member rows parsed -- table shape likely changed"

    offenders = []
    for row in data_rows:
        cell = row[-1]
        hit = FORBIDDEN_STATUS_WORDS.search(cell)
        if hit:
            offenders.append((row[1], cell, hit.group(0)))
    assert not offenders, (
        "§ 1 'Status / story' cell(s) contain a bare lifecycle-status word "
        f"(should be a story key, not a free-text state word): {offenders}"
    )


def test_status_hygiene_regex_word_boundary_does_not_false_positive():
    """Guards the guard: § 1 row 5 reads `45.2 unblocked; mason 14.1` today --
    a substring scan for `blocked` would misfire on it."""
    assert not FORBIDDEN_STATUS_WORDS.search("45.2 unblocked; mason 14.1")
    assert FORBIDDEN_STATUS_WORDS.search("blocked")
    assert FORBIDDEN_STATUS_WORDS.search("Done")  # case-insensitive


# ── § 2 skill routing (AD-2) ────────────────────────────────────────────────


ALL_STATIONS = (
    "herald",
    "doctor",
    "warden",
    "scribe",
    "marshal",
    "steward",
    "atlas",
    "mason",
)


def _other_personas_silent(root: Path, station: str, name: str) -> list[str]:
    """Every `bmad-agent-<other>` that also mentions `name` -- AD-2's 'exactly
    one' half, not just 'the named one does'."""
    return [other for other in ALL_STATIONS if other != station and _persona_mentions(root, other, name)]


# Story 46.5 landed all four consented `bmad-labs-skills` directories
# unconditionally (its own AC), but is scoped to route ONLY `release-please`
# -- the other three names' routing lines were each a DIFFERENT,
# not-yet-landed station story named directly in the register's own § 2
# rows (`mcp-builder` -> atlas 24.1, `slides-generator` -> herald 18.3,
# `multi-repo-git-ops` -> marshal 31.6; epics.md Epic 46's own boundary
# text: "Station-side halves are their own stories ... and are named in
# each story's acceptance, never restated here"). All three now have their
# persona mention landed (`bmad-agent-atlas`, `bmad-agent-herald`,
# `bmad-agent-marshal` respectively, all 2026-09-07), so this carve-out is
# empty -- the single-station routing assertion below now runs
# unconditionally for every labs skill, carved out or not (review finding:
# an earlier draft's `continue` skipped both the positive and exclusivity
# halves, silently widening the carve-out past what it needed to cover;
# fixed to skip only the positive half while a name is still carved out).
# Remove a name from this set the same day its own cited story lands the
# persona mention, never before -- kept as an empty dict (not deleted) so a
# future labs skill provisioned ahead of its station story has somewhere to
# go.
_ROUTING_STORY_NOT_YET_LANDED = {
    # empty: every consented labs skill's persona mention has landed
}


def test_skill_routing_matches_ad2_for_every_currently_provisioned_row():
    root = _repo_root()
    rows = _table_rows(_section(_register_text(root), 2))
    assert rows, "no § 2 table rows parsed at all -- table shape likely changed"
    header, data_rows = rows[0], rows[1:]
    assert header[0] == "Skill", f"§ 2 header shape changed: {header!r}"
    assert header[2] == "Wielding station", f"§ 2 header shape changed: {header!r}"
    assert data_rows, "no § 2 routing rows parsed -- table shape likely changed"

    skills_dir = root / ".claude" / "skills"
    claude_md = (root / "CLAUDE.md").read_text(encoding="utf-8")

    checked_names: list[str] = []
    for row in data_rows:
        skill_cell, station_cell = row[0], row[2]
        shape, station = _station_shape(station_cell)
        for name in _skill_names(skill_cell):
            if not _skill_dir_exists(skills_dir, name):
                # Not-yet-provisioned (bmad-os-*, bmad-testarch-*, mc-*, the
                # bmad-builder skills, eval-quality): this story never
                # asserts against a skill that does not exist yet (I/O &
                # Edge-Case Matrix).
                continue
            checked_names.append(name)
            assert not _claude_md_mentions(claude_md, name), f"CLAUDE.md must never route {name!r} (AD-2)"
            if shape == "single":
                # Story 46.5 review finding: the carve-out must skip ONLY
                # the positive "the owning station mentions it" assertion
                # for the three not-yet-landed names -- it must NOT also
                # skip the exclusivity half below, which catches a
                # DIFFERENT, still-live violation (some OTHER, wrong
                # station accidentally mentioning the skill) that has
                # nothing to do with whether the true owning station's own
                # story has landed yet.
                if name not in _ROUTING_STORY_NOT_YET_LANDED:
                    assert _persona_mentions(root, station, name), (
                        f"bmad-agent-{station} does not mention {name!r}, but "
                        f"the register names {station!r} its sole wielding "
                        f"station"
                    )
                others = _other_personas_silent(root, station, name)
                assert not others, (
                    f"{name!r} is meant to have exactly one wielding "
                    f"station ({station!r}), but bmad-agent-{{{', '.join(others)}}} "
                    f"also mention it (AD-2)"
                )

    # Not vacuous: at least the two currently-provisioned prefixes were
    # actually exercised (bmad-cis-* and skf-*, both currently multi/all
    # -station, per this story's own live finding).
    assert any(n.startswith("bmad-cis") for n in checked_names), (
        "expected the bmad-cis-* row to be checked -- register or skill tree shape changed"
    )
    assert any(n.startswith("skf-") for n in checked_names), (
        "expected the skf-* row to be checked -- register or skill tree shape changed"
    )


def test_multi_and_all_stations_rows_are_exempt_from_single_station_assertion():
    """AC: CIS (multi-station) and skf (all-stations) never get the
    single-station positive assertion, but DO get the CLAUDE.md-never half."""
    root = _repo_root()
    rows = _table_rows(_section(_register_text(root), 2))[1:]

    cis_row = next((row for row in rows if "bmad-cis" in row[0]), None)
    assert cis_row is not None, "expected a bmad-cis-* row in § 2 -- register shape changed"
    skf_row = next((row for row in rows if "skf-" in row[0]), None)
    assert skf_row is not None, "expected a skf-* row in § 2 -- register shape changed"

    assert _station_shape(cis_row[2]) == ("multi", None)
    assert _station_shape(skf_row[2]) == ("all", None)

    claude_md = (root / "CLAUDE.md").read_text(encoding="utf-8")
    for row in (cis_row, skf_row):
        for name in _skill_names(row[0]):
            assert not _claude_md_mentions(claude_md, name)


# ── § 1 wired-column agreement (the story's headline AC) ────────────────────


def _wired_base_category(cell: str) -> str:
    """`"present, 16 skills"` -> `"present"`; `"wired (1 revision behind)"` ->
    `"wired"`; a bare category (`"unwired"`, `"n/a"`, ...) is unchanged."""
    return re.split(r"[,(]", cell, maxsplit=1)[0].strip()


def test_wired_column_agrees_with_live_pipeline_truth_for_every_row():
    """The story's own Given/When/Then: `steward suite pipeline-truth`'s
    `wired` column agrees with the register for 13/13 (a disagreement is a
    finding on the register, not silently ignored). Only the `wired` stage is
    probed live (a local skills-tree/`_bmad`-dir census, no network) -- every
    other stage is stubbed out via `ProbeHooks` so this stays as fast and
    offline-safe as the rest of the suite; a one-time hand-run of the full
    live CLI (all stages) is recorded in this story's `.memlog.md` instead.
    """
    from pyforge.steward.suite import SUITE_PACKAGES, ProbeHooks, build_pipeline_truth_report

    root = _repo_root()
    rows = _table_rows(_section(_register_text(root), 1))[1:]
    register_category = {}
    for row in rows:
        names = _skill_names(row[1])
        assert names, f"§ 1 'Member (version)' cell has no backtick-quoted name: {row!r}"
        register_category[names[0]] = _wired_base_category(row[3])

    no_network_hooks = ProbeHooks(
        npm=lambda *_a: None,
        github=lambda *_a: None,
        channel=lambda *_a: None,
        recipe=lambda *_a: None,
        installed=lambda *_a: None,
        # wired: left as the real, local, offline-safe default probe.
    )
    report = build_pipeline_truth_report(root, hooks=no_network_hooks)

    assert {p.name for p in report.packages} == set(register_category), (
        "SUITE_PACKAGES and the register's § 1 member list have diverged -- "
        "13/13 agreement cannot be checked until they name the same members"
    )

    # bmad-eval-quality (pending-submission-to-conda-forge, no public channel
    # yet) and bmad-manticore (a separate, multi-GB, out-of-repo studio
    # install at $PYFORGE_STUDIO_ROOT) are genuinely operator-machine
    # artifacts -- the register's "runnable"/"wired" documents THIS
    # maintainer's own provisioned machine, which a fresh CI checkout can
    # never reproduce without installing either. Real drift on either is
    # still worth catching locally; only CI's stateless runner exempts them.
    import os

    _CI_MACHINE_ONLY_MEMBERS = {"bmad-eval-quality", "bmad-manticore"}

    disagreements = []
    for pkg in report.packages:
        live = pkg.wired.value
        expected = register_category[pkg.name]
        if live != expected:
            if os.environ.get("CI") and pkg.name in _CI_MACHINE_ONLY_MEMBERS:
                continue
            disagreements.append((pkg.name, expected, live, pkg.wired.detail))
    assert not disagreements, (
        "adoption-register.md § 1 'Wired' column disagrees with a live "
        f"steward suite pipeline-truth run (register, live, detail): {disagreements}"
    )
    assert len(SUITE_PACKAGES) == 13, "the story's own '13-row register' claim assumes 13 members"


def test_single_station_branch_is_not_dead_code(tmp_path):
    """Design Notes: branch (a) (exactly-one-station + on-disk skill) has no
    real § 2 row today. Exercises the same helper functions the live test
    above uses, against a synthetic fixture root, proving the branch works
    both when the persona mentions the skill and when it does not.
    """
    fake_root = tmp_path
    skills_dir = fake_root / ".claude" / "skills"
    persona_dir = skills_dir / "bmad-agent-herald"
    persona_dir.mkdir(parents=True)
    (persona_dir / "SKILL.md").write_text(
        "# Herald persona\n\nRoutes `bmad-os-fixture-skill` (synthetic).\n",
        encoding="utf-8",
    )
    (skills_dir / "bmad-os-fixture-skill").mkdir(parents=True)
    (skills_dir / "bmad-os-other-fixture").mkdir(parents=True)
    (fake_root / "CLAUDE.md").write_text("# CLAUDE.md\n\nNo skill routing here.\n", encoding="utf-8")

    shape, station = _station_shape("herald (studio only)")
    assert (shape, station) == ("single", "herald")

    # Positive case: on disk, persona mentions it, CLAUDE.md does not.
    assert _skill_dir_exists(skills_dir, "bmad-os-fixture-skill")
    assert _persona_mentions(fake_root, station, "bmad-os-fixture-skill")
    assert not _claude_md_mentions((fake_root / "CLAUDE.md").read_text(encoding="utf-8"), "bmad-os-fixture-skill")

    # Negative case: on disk, but the persona does NOT mention this one.
    assert _skill_dir_exists(skills_dir, "bmad-os-other-fixture")
    assert not _persona_mentions(fake_root, station, "bmad-os-other-fixture")

    # CLAUDE.md hit is caught too.
    (fake_root / "CLAUDE.md").write_text("# CLAUDE.md\n\nSee `bmad-os-fixture-skill` for details.\n", encoding="utf-8")
    assert _claude_md_mentions((fake_root / "CLAUDE.md").read_text(encoding="utf-8"), "bmad-os-fixture-skill")

    # Not-yet-provisioned: skipped, not asserted either way.
    assert not _skill_dir_exists(skills_dir, "bmad-os-never-provisioned")


# ── § 2 labs consent boundary (Story 46.5, CAP-6) ───────────────────────────


def _labs_share_skill_names(root: Path) -> set[str] | None:
    """Full labs-shipped skill names from the pixi-installed share tree
    (`.pixi/envs/pyforge-guild/share/bmad-labs-skills/skills/*`), or `None`
    if that share tree isn't present in the running test environment --
    mirrors this file's own not-yet-provisioned skip precedent."""
    share = root / ".pixi" / "envs" / "pyforge-guild" / "share" / "bmad-labs-skills" / "skills"
    if not share.is_dir():
        return None
    return {p.name for p in share.iterdir() if p.is_dir()}


def _labs_consent_violations(skills_dir: Path, share_skill_names: set[str], consent: tuple[str, ...]) -> list[str]:
    """Non-consented labs skill names that exist under `.claude/skills/` --
    the CAP-6 consent-boundary invariant (Story 46.5). Only names the SHARE
    TREE actually ships are checked -- a name absent from the share tree
    could never have been copied by `provision_plugin_skill` in the first
    place, so it can never be a labs-consent violation."""
    non_consented = sorted(set(share_skill_names) - set(consent))
    return sorted(name for name in non_consented if (skills_dir / name).is_dir())


def test_no_labs_skill_outside_the_consent_list_is_present():
    """Story 46.5 CAP-6: only the operator's four-name 2026-09-06 consent
    list (read from `provision.py`'s own `_LABS_CONSENT_SKILLS` -- never
    re-declared here, avoiding a second, divergent copy of the same list)
    may ever land under `.claude/skills/` from `bmad-labs-skills`'s
    22-skill share tree."""
    from pyforge.steward.provision import _LABS_CONSENT_SKILLS

    root = _repo_root()
    share_names = _labs_share_skill_names(root)
    if share_names is None:
        pytest.skip("bmad-labs-skills share tree not present in this environment")

    violations = _labs_consent_violations(root / ".claude" / "skills", share_names, _LABS_CONSENT_SKILLS)
    assert not violations, (
        "non-consented bmad-labs-skills director(ies) present under "
        f".claude/skills/: {violations} -- only {_LABS_CONSENT_SKILLS} are "
        "consented (2026-09-06)"
    )


def test_labs_consent_violation_check_is_not_vacuous(tmp_path):
    """Not-dead-code proof (mirrors `test_single_station_branch_is_not_dead_code`'s
    own synthetic-fixture precedent): the consent-violation check above must
    actually RED when a fifth, non-consented labs skill directory is staged
    under `.claude/skills/` -- never a check that only ever reports clean."""
    skills_dir = tmp_path / ".claude" / "skills"
    consent = ("mcp-builder", "slides-generator", "multi-repo-git-ops", "release-please")
    share_names = {"mcp-builder", "release-please", "software-research"}

    for name in ("mcp-builder", "release-please"):
        (skills_dir / name).mkdir(parents=True)

    # Positive: no non-consented dir staged yet -- clean.
    assert _labs_consent_violations(skills_dir, share_names, consent) == []

    # Stage a fifth, non-consented (but real, share-tree-present) directory
    # -- must red.
    (skills_dir / "software-research").mkdir()
    assert _labs_consent_violations(skills_dir, share_names, consent) == ["software-research"]
