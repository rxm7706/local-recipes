"""``marshal factory challenge`` -- the EGM challenger (Epic 113, CAP-298..CAP-303).

One verb, five stages, three run modes:

* **ad hoc** -- ``marshal factory challenge --project <slug> --stage <s> --target <path>``;
* **integrated** -- ``marshal factory dispatch`` runs the ``readiness`` stage on a
  story spec before its harness launches (``readiness_for_dispatch``), and a
  ``bmad-retrospective`` on a marshal epic runs ``--stage drift --epic <n>``;
* **audit** -- ``--audit`` sweeps every station's newest CAP slice and the epic range
  that decomposes it, each with the Dream entry it cites, and the repo's rules once.

A whole ``SPEC.md``, ``epics.md`` or Dream outgrows one reviewer's context, so a review
can take a slice (Story 113.14): ``--section`` cuts a CAP range, an epic range or one
heading's section out of ``--target``, and ``--dream-section`` does the same to the Dream
context, each into a Tier-3 file under ``implementation-artifacts/egm/`` whose absolute
path is what the reviewer receives. Every session has a ceiling, the stage's
``[challenge].timeout_s`` (CAP-299); a session past it is killed and unevaluable.

Every report lands under Tier 3 (``implementation-artifacts/egm/``), every run is
journaled, and the exit code carries only the verb's own refusals -- never a
finding (CAP-298). ``resolve`` turns accepted findings into memlog lines on
marshal's own Spec and nothing else, and prints the exact ``memlog.py`` command
for any other owning Spec (CAP-303, Story 113.13). Six kill switches, all default off; the
``[challenge]`` policy block is the one configuration, and absent means off.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import sys
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from pyforge.core.errors import PyforgeError
from pyforge.core.flags import FlagConfigError, read_boolean, require
from pyforge.core.process import PosixProcess, ProcessError
from pyforge.core.roster import STATIONS, long_form

from ..adapters.harness_bmadloop import render_policy_toml
from ..core import challenge as core
from ..core import policy
from ..core.harness_profile import load_packaged_profiles
from ..core.journal import JournalEntryId, Phase, build_entry, mint_run_id, prepare_for_write
from ..core.model import Verdict
from ..core.tier_routing import normalize_stage_entries, resolve_bmadloop_tier_launch
from ..core.verdict import EXIT_OK, EXIT_USAGE, exit_code_for
from .config import PolicyIOError, _read_project_policy, conventional_project_policy_path, read_repo_policy_defaults
from .config import repo_root as _default_repo_root

EGM_CHALLENGE_FLAG_KEY = "pyforge.marshal.egm_challenge"  # CAP-298, Story 113.1
EGM_POLICY_BLOCK_FLAG_KEY = "pyforge.marshal.egm_policy_block"  # CAP-299, Story 113.2
EGM_DISPATCH_READINESS_FLAG_KEY = "pyforge.marshal.egm_dispatch_readiness"  # CAP-300, Story 113.3
EGM_RETRO_DRIFT_FLAG_KEY = "pyforge.marshal.egm_retro_drift"  # CAP-301, Story 113.4
EGM_AUDIT_FLAG_KEY = "pyforge.marshal.egm_audit"  # CAP-302, Story 113.5
EGM_RESOLVE_BRIDGE_FLAG_KEY = "pyforge.marshal.egm_resolve_bridge"  # CAP-303, Story 113.6

PLUGINS_ROOT_ENV = "MARSHAL_EGM_PLUGINS_ROOT"
# Story 113.9 (operator ruling 2026-11-01): the challenger reads marshal's own model_cost_catalog
# for every --project and runs on the packaged claude profile.
CATALOG_PROJECT = "pyforge-marshal"
CHALLENGER_PROFILE = "claude"
CHAIN_STANDARD_RELPATH = "docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md"
CHAIN_STANDARD_SPEC_RELPATH = "docs/governance/spec-one-chain-per-station/SPEC.md"
CHAIN_STANDARD_DREAM_RELPATH = "docs/dreams/one-chain-per-station.md"
STORY_SPEC_TEMPLATE_RELPATH = ".claude/skills/bmad-build-auto/spec-template.md"
SPEC_TEMPLATE_RELPATH = ".claude/skills/bmad-spec/assets/spec-template.md"  # the five-field shape (Story 113.12)
MEMLOG_SCRIPT_RELPATH = "_bmad/scripts/memlog.py"
# Story 113.13 (CAP-303, operator ruling 2026-11-01): resolve writes only this project's Spec; a rules
# target another Spec governs carries that Spec's folder on its report (repo-relative target -> folder).
OWN_PROJECT = "pyforge-marshal"
RULES_OWNER_OVERRIDES: Mapping[str, str] = {
    "AGENTS.md": "_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe",
    CHAIN_STANDARD_RELPATH: "docs/governance/spec-one-chain-per-station",
}
REPORT_FILENAME = "report.json"
JOURNAL_FILENAME = "journal.jsonl"
SESSION_LOG_FILENAME = "session.log"
KIND_CHALLENGE_RUN = "challenge-run"
KIND_DISPATCH_READINESS = "dispatch-challenge-readiness"
KIND_CHALLENGE_REFUSED = "challenge-refused"
KIND_AUDIT_SKIP = "challenge-audit-skip"
SLICES_DIRNAME = core.SLICES_DIRNAME
# Story 113.14: a slice is written only under a project's Tier-3 implementation-artifacts/.
_TIER3_PARTS = ("_bmad-output", "projects")
_TIER3_DIRNAME = "implementation-artifacts"

_HELP = "Fresh-context EGM review of one chain artifact (Epic 113)."


class ChallengeRunner(Protocol):
    """Runs one session on ``root``'s files; ``target`` is the artifact under review, which the
    session's Read denies leave readable (Story 113.10). ``root`` is never the session's cwd.
    ``timeout_s`` is the stage's ceiling (Story 113.14): a session past it is killed and raises."""

    def run(
        self, *, prompt: str, model: str | None, root: Path, target: Path | None, log_path: Path, timeout_s: float
    ) -> int: ...


class ChallengeRefused(PyforgeError, Exception):
    """A refusal the verb reports with the usage code; never a finding."""


@dataclass(frozen=True)
class RunOutcome:
    run_id: str
    run_dir: Path
    report_path: Path
    report: core.ChallengeReport | None
    error: str = ""


# --- argparse ---------------------------------------------------------------


def add_factory_challenge_subparser(factory_subparsers: argparse._SubParsersAction) -> None:
    # Static help: building the parser reads no flag (a read here would WARN on every `marshal` call
    # whose tree lacks the key). The switch is enforced in the handler (`require`), which refuses
    # with the usage code while the verb stays listed (spec-feature-flag-governance:CAP-7 Q3).
    help_text = f"{_HELP} Off unless {EGM_CHALLENGE_FLAG_KEY} is on."
    parser = factory_subparsers.add_parser("challenge", help=help_text, description=help_text)
    parser.add_argument("--project", help="The BMAD project slug whose [challenge] block configures the run.")
    parser.add_argument("--stage", choices=core.STAGES, help="Which review the goldfish run.")
    parser.add_argument("--target", help="The artifact to review (repo-relative or absolute).")
    parser.add_argument(
        "--section",
        metavar="SELECTOR",
        help=(
            "Review only one section of --target, cut into a Tier-3 slice in the run's own directory "
            "(<artifact_dir>/<run>/slices/) and passed as an absolute path: CAP-298..CAP-303 (a CAP range of a SPEC.md), epic:113 or epic:112..113,115 (an "
            "epic range of an epics.md), or heading:<text> (the heading whose text is, or else starts with, <text>, "
            "through its section; a dated '## <date> ...' Dream entry runs to the next dated entry; when several "
            "headings match, heading:<text>#N picks the Nth in file order, 1-based)."
        ),
    )
    parser.add_argument(
        "--dream-section",
        metavar="SELECTOR",
        help=(
            "Give the reviewers only this section of the --project station's Dream as their Dream context, cut the "
            "same way (usually heading:<YYYY-MM-DD> — <title>, the Dream entry the target cites). Not with --audit, "
            "which cuts its own."
        ),
    )
    parser.add_argument("--epic", help="With --stage drift: the epic number whose code is read against its Spec.")
    parser.add_argument(
        "--audit",
        action="store_true",
        help=(
            "Sweep the repo rules and every station's newest CAP slice (mint) and the epic range naming it "
            "(decompose), each with the Dream entry the slice cites; never a whole SPEC.md, epics.md or Dream."
        ),
    )
    parser.add_argument(
        "--force", action="store_true", help="With --audit: re-run stations whose report already exists."
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.set_defaults(handler=run_challenge, challenge_command=None)
    subs = parser.add_subparsers(dest="challenge_command", required=False)
    resolve_p = subs.add_parser(
        "resolve",
        help="Accept or reject a report's findings: memlog lines on marshal's Spec, a printed command for any other.",
    )
    # SUPPRESS: given before or after `resolve`, the one --project survives (a subparser default would erase it).
    resolve_p.add_argument(
        "--project", default=argparse.SUPPRESS, help="The project whose Spec owns the report (required)."
    )
    resolve_p.add_argument("--report", required=True, help="Path to a challenge report.json.")
    resolve_p.add_argument("--accept", action="append", default=[], metavar="ID[:NOTE]")
    resolve_p.add_argument("--reject", action="append", default=[], metavar="ID[:REASON]")
    resolve_p.set_defaults(handler=run_challenge)


# --- flags, policy, plugin ---------------------------------------------------


def flag_on(key: str) -> bool:
    """A default-off EGM switch. A broken tree reads as off: the challenger is
    never the reason a dispatch or a retro stops."""
    try:
        return read_boolean(key, default=False)
    except FlagConfigError:
        return False


def compose_effective(slug: str) -> policy.EffectivePolicy:
    repo_defaults, _finding = read_repo_policy_defaults()
    project_data: dict[str, object] = {}
    candidate = conventional_project_policy_path(slug)
    if candidate.is_file():
        try:
            project_data = dict(_read_project_policy(candidate))
        except PolicyIOError:
            project_data = {}
    effective, _findings = policy.compose(
        project_slug=slug, repo_defaults=repo_defaults, project=project_data, flags={}
    )
    return effective


def challenge_config(effective: policy.EffectivePolicy) -> core.ChallengeConfig:
    """The composed block, or ``OFF`` while the policy-block switch is off."""
    if not flag_on(EGM_POLICY_BLOCK_FLAG_KEY):
        return core.OFF
    value = effective.challenge.value
    return core.config_from_block(value if isinstance(value, Mapping) else None)


def adapter_models(effective: policy.EffectivePolicy) -> list[str]:
    """The ``[adapter]`` (``dev``) and ``[adapter.review]`` (``review``) baselines of the station's bmad-loop policy
    that a session can still run on by the station's declared tiers (Story 113.9, narrowed by Story 113.16): a
    ``model_tier_map`` tier that leaves a stage unset runs it on its baseline, and a station with no tier map runs on
    both. What a ``marshal factory spin`` session runs on is ``spin_models``, which the ``drift`` stage reads (Story
    113.17). ``triage`` inherits ``[adapter]`` too, but a triage session authors no chain artifact. A policy that cannot
    render names no baseline."""
    try:
        rendered = tomllib.loads(render_policy_toml(effective))
    except ValueError:
        return []
    adapter = rendered.get("adapter")
    if not isinstance(adapter, Mapping):
        return []
    tier_map = effective.model_tier_map.value
    tiers = [tier for tier in tier_map.values() if isinstance(tier, Mapping)] if isinstance(tier_map, Mapping) else []
    baselines = (("dev", adapter), ("review", adapter.get("review")))
    return [
        table["model"]
        for stage, table in baselines
        if isinstance(table, Mapping)
        and isinstance(table.get("model"), str)
        and table["model"]
        and not (tiers and all(tier.get(stage) for tier in tiers))
    ]


def spin_models(effective: policy.EffectivePolicy) -> list[str]:
    """Every model a ``marshal factory spin`` session can author with (Story 113.17): the ``dev`` and ``review`` models
    of the policy spin renders for each ``model_tier_map`` tier and for a run with no declared difficulty. Read from
    that render, never from the tier map: bmad-loop has no Cursor adapter, so spin drops a Cursor tier's model and runs
    on the ``[adapter]`` baselines (Story 33.16). It reads the policy as it stands now, never
    what a past run launched. A render that fails raises ``ValueError``: spin can still run on the policy file already
    on disk, so the caller must not read a failed render as no model."""
    tier_map = effective.model_tier_map.value
    models: list[str] = []
    for difficulty in (None, *(tier_map if isinstance(tier_map, Mapping) else ())):
        resolution = resolve_bmadloop_tier_launch(effective, difficulty)
        rendered = tomllib.loads(
            render_policy_toml(
                effective, difficulty=difficulty, adapter=resolution.adapter_name, tier_resolution=resolution
            )
        )
        adapter = rendered.get("adapter")
        if not isinstance(adapter, Mapping):
            continue
        for table in (adapter.get("dev") or adapter, adapter.get("review")):
            if isinstance(table, Mapping) and isinstance(table.get("model"), str) and table["model"]:
                models.append(table["model"])
    return list(dict.fromkeys(models))


def session_models(effective: policy.EffectivePolicy, *, launch_model: str | None = None) -> list[str]:
    """Every model the station's sessions can author with (CAP-299, Stories 113.9 and 113.16): its
    ``model_tier_map`` models, the ``adapter_models`` baselines a tier can still fall to, and, in a
    dispatch, the run's resolved launch model."""
    models: list[str] = []
    tier_map = effective.model_tier_map.value
    if isinstance(tier_map, Mapping):
        for stages in tier_map.values():
            if isinstance(stages, Mapping):
                for candidates in normalize_stage_entries(stages).values():
                    models.extend(candidate.model for candidate in candidates)
    models.extend(adapter_models(effective))
    if launch_model:
        models.append(launch_model)
    return models


def challenger_catalog(slug: str, effective: policy.EffectivePolicy) -> Mapping[str, object]:
    """Marshal's own ``model_cost_catalog``, read for every ``--project`` (operator ruling
    2026-11-01, Story 113.9); ``render_refusals`` keeps only its Anthropic entries."""
    source = effective if slug == CATALOG_PROJECT else compose_effective(CATALOG_PROJECT)
    value = source.model_cost_catalog.value
    return value if isinstance(value, Mapping) else {}


def challenger_aliases() -> tuple[str, ...]:
    """The packaged claude profile's ``[model_list]`` aliases: the profile the challenger runs on."""
    profile = load_packaged_profiles().get(CHALLENGER_PROFILE)
    if profile is None or profile.model_list is None:
        return ()
    return tuple(profile.model_list.aliases)


def model_refusals(
    config: core.ChallengeConfig,
    *,
    slug: str,
    effective: policy.EffectivePolicy,
    launch_model: str | None = None,
    stage: str | None = None,
) -> list[str]:
    """``core.render_refusals`` with the challenger's catalog, the station's session models and the
    claude profile's aliases (CAP-299, Story 113.9). ``drift``'s whole target is what dev sessions wrote, so it also
    refuses a model a ``marshal factory spin`` session can run on, and refuses when spin's policy cannot render
    (CAP-301, Story 113.17)."""
    aliases = challenger_aliases()
    refusals = core.render_refusals(
        config,
        session_models=session_models(effective, launch_model=launch_model),
        model_cost_catalog=challenger_catalog(slug, effective),
        aliases=aliases,
    )
    if stage == "drift" and config.enabled:
        try:
            clashes = sorted({m for m in spin_models(effective) if core.same_model(config.model, m, aliases=aliases)})
        except ValueError as exc:
            refusals.append(f"the drift stage cannot read what marshal factory spin renders for {slug}: {exc}")
            return refusals
        if clashes:
            refusals.append(
                f"[challenge].model {config.model!r} cannot run the drift stage: the epic's code may come from "
                f"a marshal factory spin session on {', '.join(clashes)}"
            )
    return refusals


def plugins_root(env: Mapping[str, str] | None = None) -> Path:
    raw = (env if env is not None else os.environ).get(PLUGINS_ROOT_ENV)
    return Path(raw) if raw else Path.home() / ".claude" / "plugins"


def plugin_refusal(plugins: Path, version: str, personas: tuple[str, ...] = ()) -> str | None:
    """``None`` when ``egm@egm`` is enabled in the challenge session's own ``--settings`` (the
    scope the session runs with, from outside the repo -- Story 113.10), Claude Code's
    installed-plugins index holds exactly the pinned version, the cache manifest
    agrees, every persona's adapter omits the instruction files and holds
    read-only tools, and ``claude --version`` reads at or above the Claude Code
    floor that honours ``omitClaudeMd`` (Story 113.11); otherwise the reason (CAP-298, CAP-299)."""
    from ..adapters.challenge_harness import ChallengeHarnessError, claude_version, session_settings

    try:
        settings = session_settings(plugins)
    except ChallengeHarnessError as exc:
        return f"cannot render the challenge session's settings: {exc}"
    enabled = settings.get("enabledPlugins")
    if not isinstance(enabled, Mapping) or enabled.get(core.EGM_PLUGIN_ID) is not True:
        return f"{core.EGM_PLUGIN_ID} is not enabled in the challenge session's --settings"
    try:
        installed = json.loads((plugins / "installed_plugins.json").read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        installed = {}
    refusal = core.installed_version_refusal(installed, core.EGM_PLUGIN_ID, version)
    if refusal:
        return f"{refusal}; run: claude plugin install {core.EGM_PLUGIN_ID}"
    plugin_dir = plugins / "cache" / core.EGM_MARKETPLACE / "egm" / version
    try:
        manifest = json.loads((plugin_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return f"the EGM plugin {version} is not in the plugin cache ({plugin_dir})"
    if manifest.get("version") != version:
        return f"the cached EGM plugin reports {manifest.get('version')!r}, not the pinned {version!r}"
    for persona in personas:
        adapter = plugin_dir / ".claude-plugin" / "agents" / core.ADAPTER_FILES[persona]
        try:
            text = adapter.read_text(encoding="utf-8")
        except OSError:
            return f"the EGM adapter for {persona!r} is missing ({adapter})"
        violations = core.adapter_isolation_violations(persona, text)
        if violations:
            return "; ".join(violations)
    return core.claude_code_version_refusal(claude_version())


# --- paths -------------------------------------------------------------------


def _abs(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else (root / candidate)


def glossary_path(root: Path, slug: str) -> Path:
    return root / "_bmad-output" / "projects" / slug / "planning-artifacts" / "specs" / f"spec-{slug}" / "glossary.md"


def spec_path(root: Path, slug: str) -> Path:
    return glossary_path(root, slug).with_name("SPEC.md")


def dream_path(root: Path, slug: str) -> Path:
    return root / "docs" / "dreams" / f"{slug}.md"


def epics_path(root: Path, slug: str) -> Path:
    return root / "_bmad-output" / "projects" / slug / "planning-artifacts" / "epics.md"


def station_skill_path(root: Path, station: str) -> Path | None:
    name = long_form(station)
    for candidate in (
        root / ".claude" / "skills" / name / "active" / name / "SKILL.md",
        root / ".claude" / "skills" / name / "SKILL.md",
    ):
        if candidate.is_file():
            return candidate
    return None


def owner_override(root: Path, stage: str, target: Path) -> Path | None:
    """The Spec folder that governs a rules target outside its run's station (Story 113.13, CAP-303):
    ``AGENTS.md`` is ``spec-pyforge-scribe``'s, ``CHAIN-STANDARD.md`` ``spec-one-chain-per-station``'s."""
    if stage != "rules":
        return None
    resolved = _abs(root, target)
    for relpath, workspace in RULES_OWNER_OVERRIDES.items():
        if resolved == root / relpath:
            return root / workspace
    return None


def owning_spec(root: Path, slug: str, stage: str, target: Path) -> Path:
    """The Spec folder a run's findings belong to: the override, else the station's own Spec."""
    return owner_override(root, stage, target) or spec_path(root, slug).parent


def artifact_dir(root: Path, slug: str, config: core.ChallengeConfig) -> Path:
    return root / "_bmad-output" / "projects" / slug / config.artifact_dir


def default_standards(root: Path, slug: str, stage: str) -> tuple[Path, ...]:
    """Each stage's standard when the ``[challenge]`` block names none for it (CAP-299, Story 113.12):
    mint is judged against the bmad-spec five-field template, decompose against the station Spec whose
    capability range its stories claim; both also against the chain standard."""
    if stage == "mint":
        return (root / CHAIN_STANDARD_RELPATH, root / SPEC_TEMPLATE_RELPATH)
    if stage == "decompose":
        return (root / CHAIN_STANDARD_RELPATH, spec_path(root, slug))
    if stage == "rules":
        return (root / CHAIN_STANDARD_RELPATH,)
    if stage == "readiness":
        return (root / STORY_SPEC_TEMPLATE_RELPATH,)
    return (spec_path(root, slug),)  # drift: the code is judged against the Spec


def build_context(
    root: Path,
    slug: str,
    stage: str,
    target: Path,
    config: core.ChallengeConfig,
    *,
    dream: Path | None = None,
    standards_fallback: tuple[Path, ...] = (),
    omit_dream: bool = False,
) -> core.ChallengeContext:
    """The reviewer's context. A block's ``standards`` entry for the stage wins; else ``standards_fallback`` (the
    audit's decompose run reads the CAP slice its epics claim, Story 113.14); else ``default_standards``. The Dream
    is ``dream``, else the station's whole Dream, unless ``omit_dream`` (an audit run with no entry to cut) gives
    the reviewer none."""
    standards = (
        tuple(_abs(root, s) for s in config.standards.get(stage, ()))
        or standards_fallback
        or default_standards(root, slug, stage)
    )
    return core.ChallengeContext(
        target=str(_abs(root, target)),
        glossary=str(glossary_path(root, slug)) if glossary_path(root, slug).is_file() else "",
        dream="" if omit_dream else str(dream or dream_path(root, slug)),
        standards=tuple(str(s) for s in standards),
    )


# --- journal -----------------------------------------------------------------


def _ts(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _utc_compact(moment: datetime) -> str:
    return moment.strftime("%Y%m%dT%H%M%S") + f"{moment.microsecond // 1000:03d}Z"


def append_journal(
    journal: Path,
    *,
    writer: str,
    counter: int,
    run_id: str,
    kind: str,
    phase: Phase,
    payload: Mapping[str, object],
    now: datetime,
    intent: JournalEntryId | None = None,
) -> JournalEntryId:
    entry_id = JournalEntryId(writer, counter)
    entry = build_entry(
        id=entry_id, ts=_ts(now), run_id=run_id, kind=kind, phase=phase, payload=dict(payload), intent_id=intent
    )
    prepared = prepare_for_write(entry)
    if prepared.sidecar_relative_path is not None:
        sidecar = journal.parent / prepared.sidecar_relative_path
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(prepared.sidecar_content or "", encoding="utf-8")
    with journal.open("a", encoding="utf-8") as handle:
        handle.write(prepared.line + "\n")
    return entry_id


def tree_snapshot(root: Path) -> str | None:
    """``git status --porcelain`` at ``root``; ``None`` when it is not a git tree."""
    try:
        done = PosixProcess().run(["git", "status", "--porcelain"], cwd=root, timeout_s=60)
    except ProcessError:
        return None
    return done.stdout if done.returncode == 0 else None


def journal_refusal(out_dir: Path, slug: str, reason: str, now: datetime) -> Path:
    """S6: a refusal is a journaled fact, not only a line on stderr."""
    run_id = mint_run_id(slug, _utc_compact(now), secrets.token_hex(4))
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    append_journal(
        run_dir / JOURNAL_FILENAME,
        writer=f"challenge-{secrets.token_hex(3)}",
        counter=0,
        run_id=run_id,
        kind=KIND_CHALLENGE_REFUSED,
        phase=Phase.OBSERVATION,
        payload={"project": slug, "reason": reason},
        now=now,
    )
    return run_dir


# --- one challenge -------------------------------------------------------------


def new_run_dir(out_dir: Path, slug: str, moment: datetime) -> Path:
    """A fresh run directory, named by its run id, under ``out_dir``."""
    run_dir = out_dir / mint_run_id(slug, _utc_compact(moment), secrets.token_hex(4))
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def run_one(
    *,
    root: Path,
    slug: str,
    stage: str,
    target: Path,
    config: core.ChallengeConfig,
    runner: ChallengeRunner,
    out_dir: Path,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    dream: Path | None = None,
    owner: Path | None = None,
    standards: tuple[Path, ...] = (),
    dream_choice: str = "",
    omit_dream: bool = False,
    run_dir: Path | None = None,
) -> RunOutcome:
    """Run one stage on one target. Refusals raise ``ChallengeRefused`` before
    anything is written; a session that fails, outlives its ``[challenge].timeout_s``
    ceiling, writes no valid report, or writes one that omits a dispatched reviewer or
    names another stage is an ``error`` on the outcome (unevaluable, ``report`` is
    ``None``), never a finding. ``owner`` is the Spec folder the findings belong to
    (default ``owning_spec``); ``standards`` is ``build_context``'s fallback; ``dream_choice`` (the audit's
    ``cited``, ``names-cap`` or ``newest``) is journaled with the intent so a reader can tell a weak fallback.
    ``run_dir`` is a run directory the caller already made (``new_run_dir``) to hold the run's own slices."""
    context = build_context(
        root, slug, stage, target, config, dream=dream, standards_fallback=standards, omit_dream=omit_dream
    )
    violations = core.context_violations(context)
    if violations:
        raise ChallengeRefused("; ".join(violations))
    for path in (context.target, *context.context_paths()):
        if not Path(path).is_file():
            raise ChallengeRefused(f"{path} does not exist")
    moment = now()
    run_dir = run_dir or new_run_dir(out_dir, slug, moment)
    run_id = run_dir.name
    report_path = run_dir / REPORT_FILENAME
    journal = run_dir / JOURNAL_FILENAME
    personas = config.reviewers_for(stage)
    timeout_s = config.timeout_for(stage)
    prompt = core.render_prompt(stage=stage, personas=personas, context=context, report_path=str(report_path))
    writer = f"challenge-{secrets.token_hex(3)}"
    intent = append_journal(
        journal,
        writer=writer,
        counter=0,
        run_id=run_id,
        kind=KIND_CHALLENGE_RUN,
        phase=Phase.INTENT,
        payload={
            "project": slug,
            "stage": stage,
            "target": context.target,
            "reviewers": [core.agent_type(p) for p in personas],
            "model": config.model,
            "plugin_version": config.plugin_version,
            "timeout_s": timeout_s,
            **({"dream": context.dream, "dream_choice": dream_choice} if dream_choice else {}),
            "report": str(report_path),
        },
        now=moment,
    )
    error = ""
    report: core.ChallengeReport | None = None
    before = tree_snapshot(root)
    try:
        returncode = runner.run(
            prompt=prompt,
            model=config.model or None,
            root=root,
            target=Path(context.target),
            log_path=run_dir / SESSION_LOG_FILENAME,
            timeout_s=timeout_s,
        )
        if returncode != 0:
            error = f"challenge session exited {returncode}"
    except Exception as exc:  # the harness adapter's own error, or an OS failure
        error = f"challenge session did not run: {exc}"
    after = tree_snapshot(root)
    tree_changed = before is not None and after is not None and before != after
    if tree_changed and not error:
        error = "the challenge session changed the working tree; its report is not trusted"
    if not error:
        try:
            report = core.parse_report(report_path.read_text(encoding="utf-8"))
        except (OSError, core.ReportError) as exc:
            error = f"no valid report at {report_path}: {exc}"
    if report is not None:
        reason = core.unevaluable_reason(report, stage=stage, personas=personas)
        if reason:
            error = f"the report at {report_path} is unevaluable: {reason}"
            report = None
    if report is not None:
        workspace = owner or owning_spec(root, slug, stage, target)
        override = "" if workspace == spec_path(root, slug).parent else str(workspace)
        report = core.with_provenance(report, project=slug, spec_workspace=str(workspace), owner_override=override)
        report_path.write_text(report.to_json() + "\n", encoding="utf-8")
    append_journal(
        journal,
        writer=writer,
        counter=1,
        run_id=run_id,
        kind=KIND_CHALLENGE_RUN,
        phase=Phase.OUTCOME,
        payload={
            "status": "error" if error else "reported",
            "error": error,
            "tree_changed": tree_changed,
            "findings": len(report.findings) if report else 0,
            "high": sum(1 for f in report.findings if f.severity == "high") if report else 0,
            "report": str(report_path),
        },
        now=now(),
        intent=intent,
    )
    return RunOutcome(run_id=run_id, run_dir=run_dir, report_path=report_path, report=report, error=error)


# --- drift (CAP-301) -----------------------------------------------------------

_EPIC_HEADING = re.compile(r"^## Epic (?P<n>\d+)\b")
_SPEC_LINE = re.compile(r"^\*\*Spec:\*\*\s*`(?P<path>[^`]+)`")
_SRC_PATH = re.compile(r"`(?P<path>src/[^`\s]+)`")


def epic_drift_paths(epics_text: str, epic: str) -> tuple[list[str], list[str]]:
    """The epic's story-spec paths and the ``src/`` paths its stories name."""
    specs: list[str] = []
    sources: list[str] = []
    inside = False
    for line in epics_text.splitlines():
        heading = _EPIC_HEADING.match(line)
        if heading:
            inside = heading.group("n") == str(epic)
            continue
        if inside and line.startswith("## "):
            inside = False
        if not inside:
            continue
        spec = _SPEC_LINE.match(line)
        if spec:
            specs.append(spec.group("path"))
        if line.startswith("**Surface:**"):
            sources.extend(m.group("path") for m in _SRC_PATH.finditer(line))
    return specs, sorted(dict.fromkeys(sources))


def write_drift_target(root: Path, slug: str, epic: str, out_dir: Path) -> Path:
    text = epics_path(root, slug).read_text(encoding="utf-8")
    specs, sources = epic_drift_paths(text, epic)
    if not specs:
        raise ChallengeRefused(f"epic {epic} has no story specs in {epics_path(root, slug)}")
    planning = epics_path(root, slug).parent
    lines = [f"# Drift target — {slug} epic {epic}", "", "## Story specs", ""]
    lines += [f"- {(planning.parent / s) if s.startswith('planning-artifacts/') else _abs(root, s)}" for s in specs]
    lines += ["", "## Source paths the stories name", ""]
    lines += [f"- {root / s}" for s in sources if (root / s).exists()] or ["- (none named)"]
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"drift-epic-{epic}.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


# --- slices (Story 113.14) ----------------------------------------------------------


def _require_tier3(root: Path, path: Path) -> None:
    """Refuse ``path`` unless it lies under a project's Tier-3 ``implementation-artifacts/``, judged on the path as
    written, so a ``..`` part (``implementation-artifacts/../planning-artifacts``) is refused, never followed."""
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = ()
    if ".." in path.parts or len(parts) < 4 or parts[:2] != _TIER3_PARTS or parts[3] != _TIER3_DIRNAME:
        raise ChallengeRefused(
            f"{path} is not under a project's Tier-3 {_TIER3_DIRNAME}/; slices are written only there"
        )


def _write_tier3(root: Path, out_dir: Path, name: str, text: str) -> Path:
    """Write ``text`` as ``out_dir / name`` under Tier 3 (``_require_tier3``); return the file's absolute path, the
    form a reviewer receives."""
    _require_tier3(root, out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = Path(os.path.abspath(out_dir / name))
    path.write_text(text, encoding="utf-8")
    return path


def _read_source(source: Path) -> str:
    try:
        return source.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:  # ValueError: an undecodable file (UnicodeDecodeError) refuses, never crashes
        raise ChallengeRefused(f"cannot read {source} to slice it: {exc}") from exc


def cut_slice(source: Path, selector: core.Selector) -> tuple[str, str]:
    """``(file name, text)`` of ``selector``'s section of ``source``, cut in memory so a selector that names
    nothing refuses before anything is written."""
    try:
        section = core.select_section(_read_source(source), selector)
    except core.SelectorError as exc:
        raise ChallengeRefused(f"{source}: {exc}") from exc
    return f"{source.stem}--{selector.slug}.md", section


def write_slice(root: Path, source: Path, selector: core.Selector, out_dir: Path) -> Path:
    """Cut ``selector``'s section of ``source`` into a Tier-3 file under ``out_dir`` holding exactly that section,
    the way ``write_drift_target`` writes the drift target (Story 113.14, CAP-302)."""
    return _write_tier3(root, out_dir, *cut_slice(source, selector))


def write_dream_entry(root: Path, slug: str, cap_slice: core.CapSlice, out_dir: Path) -> tuple[Path, str]:
    """The Dream entry ``cap_slice`` takes, cut from the station's Dream into a Tier-3 file, and the rule that chose
    it (``core.dream_entry_section``): the entry it cites, else the newest entry naming one of its CAPs, else the
    newest dated entry."""
    dream = dream_path(root, slug)
    try:
        heading, section, choice = core.dream_entry_section(
            _read_source(dream),
            cap_slice.dream_date,
            cap_slice.dream_title,
            caps=range(cap_slice.first, cap_slice.last + 1),
            own_spec=spec_path(root, slug).parent.name,
        )
    except core.SelectorError as exc:
        raise ChallengeRefused(f"{dream}: {exc}") from exc
    return _write_tier3(root, out_dir, f"{dream.stem}--dream-entry-{heading[:10]}.md", section), choice


# --- audit (CAP-302) -------------------------------------------------------------


@dataclass(frozen=True)
class AuditRun:
    """One review the sweep makes. ``dream`` ``None`` gives the reviewer no Dream (a station skill's rules run when
    its station has no slice) -- never the whole station Dream;
    ``standards`` is ``build_context``'s fallback (the decompose run's CAP slice); ``dream_choice`` is the rule that
    chose the Dream entry (``cited``, ``names-cap`` or ``newest``) of a mint or decompose run and of a station
    skill's rules run, which borrows its station's mint entry; it is empty for a repo-rules run, which reads
    ``one-chain-per-station.md``, and for a skill run whose station has no slice (no Dream)."""

    slug: str
    stage: str
    target: Path
    dream: Path | None
    owner: Path
    standards: tuple[Path, ...] = ()
    dream_choice: str = ""


def _station_slices(root: Path, slug: str, out_dir: Path) -> tuple[list[AuditRun], list[str]]:
    """A station's mint run (its newest CAP slice) and decompose run (the epic range whose headings name a CAP
    of that slice), both with the Dream entry the slice cites -- read from the station's own Spec only
    (operator ruling 2026-11-01) -- and, for a run whose slice cannot be cut, why."""
    spec = spec_path(root, slug)
    try:
        cap_slice = core.newest_cap_slice(_read_source(spec))
        if cap_slice is None:
            raise ChallengeRefused(f"{spec} defines no CAP")
        caps = write_slice(root, spec, cap_slice.selector, out_dir)
        dream, choice = write_dream_entry(root, slug, cap_slice, out_dir)
    except (OSError, ValueError, ChallengeRefused) as exc:
        return [], [f"{slug} mint and decompose: no slice: {exc}"]
    runs = [AuditRun(slug, "mint", caps, dream, spec.parent, dream_choice=choice)]
    epics = epics_path(root, slug)
    try:
        epic_range = core.epics_naming(_read_source(epics), cap_slice, spec.parent.name)
        if epic_range is None:
            raise ChallengeRefused(f"no '## Epic' heading in {epics} names {cap_slice.selector.slug}")
        decomposed = write_slice(root, epics, epic_range, out_dir)
    except (OSError, ValueError, ChallengeRefused) as exc:
        return runs, [f"{slug} decompose: no slice: {exc}"]
    standards = (root / CHAIN_STANDARD_RELPATH, caps)
    runs.append(AuditRun(slug, "decompose", decomposed, dream, spec.parent, standards, dream_choice=choice))
    return runs, []


def audit_plan(root: Path, slice_dir: Path) -> tuple[list[AuditRun], list[str]]:
    """Every audit run, in order, and why any station's slice could not be cut: the repo rules first, then each
    station's skill (rules), its newest CAP slice (mint) and the epic range that decomposes it (decompose), the
    slices written under ``slice_dir/<slug>/`` -- never a whole ``SPEC.md``, ``epics.md`` or Dream, and never a
    story spec, which the readiness stage reads (Story 113.14). The repo rules run under marshal but carry their
    governor's Spec (``owning_spec``, Story 113.13)."""
    runs: list[AuditRun] = [
        AuditRun(
            OWN_PROJECT,
            "rules",
            target,
            root / CHAIN_STANDARD_DREAM_RELPATH,
            owning_spec(root, OWN_PROJECT, "rules", target),
        )
        for target in (root / "AGENTS.md", root / CHAIN_STANDARD_RELPATH)
    ]
    gaps: list[str] = []
    for station in STATIONS:
        slug = long_form(station)
        station_runs, station_gaps = _station_slices(root, slug, slice_dir / slug)
        skill = station_skill_path(root, station)
        if skill is not None:
            # the skill is read against the Dream entry its station's mint run takes, else against no Dream
            mint = next((run for run in station_runs if run.stage == "mint"), None)
            dream, choice = (mint.dream, mint.dream_choice) if mint is not None else (None, "")
            owner = owning_spec(root, slug, "rules", skill)
            runs.append(AuditRun(slug, "rules", skill, dream, owner, dream_choice=choice))
        runs.extend(station_runs)
        gaps.extend(station_gaps)
    return runs, gaps


def run_audit(
    *,
    root: Path,
    config: core.ChallengeConfig,
    runner: ChallengeRunner,
    out_root: Path,
    force: bool,
    now: Callable[[], datetime],
) -> tuple[Path, dict[str, list[core.ChallengeReport]], list[str]]:
    audit_dir = out_root / f"audit-{now().date().isoformat()}"
    audit_dir.mkdir(parents=True, exist_ok=True)
    reports: dict[str, list[core.ChallengeReport]] = {}
    errors: list[str] = []
    audit_journal = audit_dir / JOURNAL_FILENAME
    writer = f"challenge-audit-{secrets.token_hex(3)}"
    counter = 0
    plan, gaps = audit_plan(root, audit_dir / SLICES_DIRNAME)
    errors.extend(gaps)  # a station the sweep could not slice did not report: the sweep is unevaluable
    for run in plan:
        slug, stage, target = run.slug, run.stage, run.target
        marker = audit_dir / f"{slug}.{stage}.{target.name}.json"
        if marker.is_file() and not force:
            try:
                kept = core.parse_report(marker.read_text(encoding="utf-8"))
                if core.unevaluable_reason(kept, stage=stage, personas=config.reviewers_for(stage)):
                    raise core.ReportError("an incomplete marker")
            except OSError, core.ReportError:
                pass  # a corrupt or incomplete marker is re-run below
            else:
                reports.setdefault(slug, []).append(kept)
                append_journal(
                    audit_journal,
                    writer=writer,
                    counter=counter,
                    run_id=audit_dir.name,
                    kind=KIND_AUDIT_SKIP,
                    phase=Phase.OBSERVATION,
                    payload={"project": slug, "stage": stage, "target": str(target), "marker": str(marker)},
                    now=now(),
                )
                counter += 1
                continue
        try:
            outcome = run_one(
                root=root,
                slug=slug,
                stage=stage,
                target=target,
                config=config,
                runner=runner,
                out_dir=audit_dir / "runs",
                now=now,
                dream=run.dream,
                owner=run.owner,
                standards=run.standards,
                dream_choice=run.dream_choice,
                omit_dream=run.dream is None,
            )
        except ChallengeRefused as exc:
            errors.append(f"{slug} {stage} {target.name}: refused: {exc}")
            continue
        if outcome.report is None:
            errors.append(f"{slug} {stage} {target.name}: {outcome.error}")
            continue
        marker.write_text(outcome.report.to_json() + "\n", encoding="utf-8")
        reports.setdefault(slug, []).append(outcome.report)
    for slug, station_reports in reports.items():
        (audit_dir / f"{slug}.md").write_text(core.fleet_summary({slug: station_reports}), encoding="utf-8")
    (audit_dir / "fleet.md").write_text(core.fleet_summary(reports), encoding="utf-8")
    return audit_dir, reports, errors


# --- resolve (CAP-303) -------------------------------------------------------------


def append_memlog(root: Path, workspace: str, text: str) -> None:
    argv = [sys.executable, str(root / MEMLOG_SCRIPT_RELPATH), "append", "--workspace", workspace]
    try:
        done = PosixProcess().run([*argv, "--type", "event", "--text", text], cwd=root, timeout_s=60)
    except ProcessError as exc:
        raise core.ReportError(f"memlog append did not run: {exc}") from exc
    if done.returncode != 0:
        raise core.ReportError(f"memlog append failed: {done.stderr.strip() or done.stdout.strip()}")


def _names(recorded: str, root: Path, expected: Path) -> bool:
    """``recorded`` (a report's Spec folder) names ``expected``: the same path, or one ending in its
    repo-relative parts (a report written in another checkout of this repo)."""
    if not recorded:
        return False
    tail = expected.relative_to(root).parts
    return _abs(root, recorded) == expected or Path(recorded).parts[-len(tail) :] == tail


def resolve_owner(root: Path, project: str, report: core.ChallengeReport) -> Path:
    """The Spec folder ``resolve`` acts on (Story 113.13, CAP-303), derived from ``--project``, or for
    a rules report that records an owner override, from ``RULES_OWNER_OVERRIDES``; never taken from
    the report. The report's ``spec_workspace`` must name it, or ``ReportError``."""
    candidates = [spec_path(root, project).parent]
    if report.stage == "rules" and report.owner_override:
        candidates += [
            root / ws for ws in RULES_OWNER_OVERRIDES.values() if _names(report.owner_override, root, root / ws)
        ]
    for candidate in candidates:
        if _names(report.spec_workspace, root, candidate):
            return candidate
    named = ", ".join(c.relative_to(root).as_posix() for c in candidates)
    raise core.ReportError(
        f"the report's spec_workspace {report.spec_workspace or '(none)'!r} is not the Spec --project {project} "
        f"or its owner override names ({named}); nothing was written"
    )


def run_resolve(args: argparse.Namespace, *, root: Path, memlog: Callable[[Path, str, str], None]) -> int:
    """Marshal writes only its own Spec (Story 113.13): an accepted finding another Spec owns is printed
    as the exact ``memlog.py`` command the operator runs; rejections go back into the report either way."""
    require(EGM_RESOLVE_BRIDGE_FLAG_KEY)
    report_path = _abs(root, args.report)
    project = getattr(args, "project", None)
    try:
        if not project:
            raise core.ReportError("--project is required: resolve derives the owning Spec from it")
        report = core.parse_report(report_path.read_text(encoding="utf-8"))
        owner = resolve_owner(root, project, report)
        accept = core.parse_id_notes(args.accept)
        reject = core.parse_id_notes(args.reject)
        resolution = core.resolve(report, accept=accept, reject=reject, report_path=str(report_path))
    except (OSError, core.ReportError) as exc:
        print(f"marshal factory challenge resolve: {exc}", file=sys.stderr)
        return EXIT_USAGE
    workspace = owner.relative_to(root).as_posix()
    if owner != spec_path(root, OWN_PROJECT).parent:
        for line in resolution.memlog_lines:
            print(core.memlog_command(script=MEMLOG_SCRIPT_RELPATH, workspace=workspace, text=line))
        report_path.write_text(resolution.report.to_json() + "\n", encoding="utf-8")
        print(f"resolved: {len(accept)} accepted (no memlog line written), {len(reject)} rejected")
        if resolution.memlog_lines:
            print(
                f"next: marshal writes only {OWN_PROJECT}'s Spec; run the {len(resolution.memlog_lines)} command(s) "
                f"above for {workspace}, then re-derive that Spec with bmad-spec in the same change"
            )
        return EXIT_OK
    try:
        for line in resolution.memlog_lines:
            memlog(root, str(owner), line)
    except core.ReportError as exc:
        print(f"marshal factory challenge resolve: {exc}; the report is unchanged", file=sys.stderr)
        return EXIT_USAGE
    report_path.write_text(resolution.report.to_json() + "\n", encoding="utf-8")
    print(f"resolved: {len(accept)} accepted (memlog lines on {workspace}), {len(reject)} rejected")
    if resolution.memlog_lines:
        print("next: re-derive the Spec with bmad-spec in the same change, so chain-currency reads both together")
    return EXIT_OK


# --- the handler -----------------------------------------------------------------


def run_challenge(
    args: argparse.Namespace,
    *,
    runner: ChallengeRunner | None = None,
    root: Path | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    memlog: Callable[[Path, str, str], None] = append_memlog,
) -> int:
    require(EGM_CHALLENGE_FLAG_KEY)
    root = root or _default_repo_root()
    if getattr(args, "challenge_command", None) == "resolve":
        return run_resolve(args, root=root, memlog=memlog)
    require(EGM_POLICY_BLOCK_FLAG_KEY)
    try:
        return _run(args, runner=runner, root=root, now=now)
    except ChallengeRefused as exc:
        print(f"marshal factory challenge: {exc}", file=sys.stderr)
        return EXIT_USAGE


def _run(args: argparse.Namespace, *, runner: ChallengeRunner | None, root: Path, now: Callable[[], datetime]) -> int:
    slug = args.project or ("pyforge-marshal" if args.audit else None)
    if not slug:
        raise ChallengeRefused("--project is required")
    effective = compose_effective(slug)
    config = challenge_config(effective)
    if not config.enabled:
        raise ChallengeRefused(f"the challenger is off for {slug}: no enabled [challenge] block")
    refusals = model_refusals(config, slug=slug, effective=effective, stage=args.stage)
    if refusals:
        raise ChallengeRefused("; ".join(refusals))
    if args.audit:
        require(EGM_AUDIT_FLAG_KEY)
    elif args.stage == "drift":
        require(EGM_RETRO_DRIFT_FLAG_KEY)
    section, dream_section = _selectors(args)
    plugins = plugins_root()
    personas = tuple(dict.fromkeys(p for stage in core.STAGES for p in config.reviewers_for(stage)))
    refusal = plugin_refusal(plugins, config.plugin_version, personas)
    if refusal:
        journal_refusal(artifact_dir(root, slug, config), slug, refusal, now())
        raise ChallengeRefused(refusal)
    if runner is None:
        from ..adapters.challenge_harness import ClaudeChallengeRunner

        runner = ClaudeChallengeRunner(plugins_root=plugins)
    out_root = artifact_dir(root, slug, config)
    if args.audit:
        audit_dir, reports, errors = run_audit(
            root=root, config=config, runner=runner, out_root=out_root, force=args.force, now=now
        )
        total = sum(len(r.findings) for rs in reports.values() for r in rs)
        _emit(args, {"audit_dir": str(audit_dir), "stations": len(reports), "findings": total, "errors": errors})
        # CAP-302: one station that did not report makes the sweep unevaluable; findings never do.
        return exit_code_for(Verdict.UNEVALUABLE) if errors else EXIT_OK
    if not args.stage:
        raise ChallengeRefused("--stage is required (or --audit)")
    if args.stage == "drift":
        if not args.epic:
            raise ChallengeRefused("--stage drift needs --epic <n>")
        target = write_drift_target(root, slug, args.epic, out_root / "drift")
    elif args.target:
        target = _abs(root, args.target)
    else:
        raise ChallengeRefused("--target is required for this stage")
    # Cut in memory first, so a selector that names nothing refuses before anything is written; the slices then go
    # into this run's own directory, so two runs never overwrite each other's (Story 113.14).
    target_cut = cut_slice(target, section) if section is not None else None
    dream_cut = cut_slice(dream_path(root, slug), dream_section) if dream_section is not None else None
    run_dir: Path | None = None
    dream: Path | None = None
    if target_cut is not None or dream_cut is not None:
        _require_tier3(root, out_root)
        run_dir = new_run_dir(out_root, slug, now())
        if target_cut is not None:
            target = _write_tier3(root, run_dir / SLICES_DIRNAME, *target_cut)
        if dream_cut is not None:
            dream = _write_tier3(root, run_dir / SLICES_DIRNAME, *dream_cut)
    try:
        outcome = run_one(
            root=root,
            slug=slug,
            stage=args.stage,
            target=target,
            config=config,
            runner=runner,
            out_dir=out_root,
            now=now,
            dream=dream,
            run_dir=run_dir,
        )
    except ChallengeRefused:
        if run_dir is not None:  # a refusal leaves no orphan <run_id>/slices/ behind
            shutil.rmtree(run_dir, ignore_errors=True)
        raise
    _emit(
        args,
        {
            "run_id": outcome.run_id,
            "report": str(outcome.report_path),
            "findings": len(outcome.report.findings) if outcome.report else 0,
            "error": outcome.error,
        },
    )
    return exit_code_for(Verdict.UNEVALUABLE) if outcome.error else EXIT_OK


def _selectors(args: argparse.Namespace) -> tuple[core.Selector | None, core.Selector | None]:
    """``--section`` and ``--dream-section``, parsed before anything is written (Story 113.14)."""
    raw_section, raw_dream = getattr(args, "section", None), getattr(args, "dream_section", None)
    if args.audit and (raw_section or raw_dream):
        raise ChallengeRefused("--section and --dream-section slice an ad hoc run; --audit cuts its own slices")
    if raw_section and (args.stage == "drift" or not args.target):
        raise ChallengeRefused("--section slices --target (a drift run writes its own target)")
    try:
        return (
            core.parse_selector(raw_section) if raw_section else None,
            core.parse_selector(raw_dream) if raw_dream else None,
        )
    except core.SelectorError as exc:
        raise ChallengeRefused(str(exc)) from exc


def _emit(args: argparse.Namespace, data: Mapping[str, object]) -> None:
    if getattr(args, "format", "text") == "json":
        print(json.dumps(dict(data), sort_keys=True))
        return
    for key, value in data.items():
        print(f"{key}: {value}")


# --- the dispatch hook (CAP-300) -----------------------------------------------------


@dataclass(frozen=True)
class ReadinessResult:
    """What the dispatch hook journals and reports. ``ran`` is False when the
    hook is off; then dispatch proceeds byte-identically."""

    ran: bool
    report_path: str = ""
    findings: int = 0
    high: int = 0
    error: str = ""


def readiness_for_dispatch(
    *,
    root: Path,
    slug: str,
    story_spec: Path,
    effective: policy.EffectivePolicy,
    runner: ChallengeRunner | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    plugins: Path | None = None,
    launch_model: str | None = None,
) -> ReadinessResult:
    """Run the readiness stage before a dispatch's harness launches, when the
    switch is on and the station's block names the stage. Report only: never a
    status move, never a ledger write, never a refusal of the dispatch. The
    challenger is never ``launch_model``, the run's resolved launch model (Story 113.9).
    The wait is bounded by the block's ``timeout_s.readiness`` (default 600 s, Story 113.14):
    a session past it is killed and reported as an unevaluable result, and the dispatch proceeds.
    With a tier map and no ``launch_model``, ``MRS-DISP-043`` dropped the run's override: the session runs on the
    harness's own default, which no policy names, so the review refuses (Story 113.16)."""
    if not flag_on(EGM_CHALLENGE_FLAG_KEY) or not flag_on(EGM_DISPATCH_READINESS_FLAG_KEY):
        return ReadinessResult(ran=False)
    config = challenge_config(effective)
    if not config.stage_on("readiness"):
        return ReadinessResult(ran=False)
    # Everything else the block says -- the model, standards, artifact_dir, plugin_version and the readiness
    # ceiling (``timeout_s``, Story 113.14) -- carries over unchanged.
    one = replace(config, enabled=True, stages=("readiness",), reviewers={"readiness": ("implementation-readiness",)})
    refusals = model_refusals(one, slug=slug, effective=effective, launch_model=launch_model)
    if launch_model is None and effective.model_tier_map.value:
        refusals.append(
            "the run launches on the harness's own default (its model override was dropped), "
            "which cannot be shown to differ from [challenge].model"
        )
    plugins = plugins or plugins_root()
    refusal = "; ".join(refusals) or plugin_refusal(plugins, one.plugin_version, ("implementation-readiness",))
    if refusal:
        return ReadinessResult(ran=True, error=f"readiness challenge refused: {refusal}")
    if runner is None:
        from ..adapters.challenge_harness import ClaudeChallengeRunner

        runner = ClaudeChallengeRunner(plugins_root=plugins)
    try:
        outcome = run_one(
            root=root,
            slug=slug,
            stage="readiness",
            target=story_spec,
            config=one,
            runner=runner,
            out_dir=artifact_dir(root, slug, one),
            now=now,
        )
    except ChallengeRefused as exc:
        return ReadinessResult(ran=True, error=f"readiness challenge refused: {exc}")
    if outcome.report is None:
        return ReadinessResult(ran=True, report_path=str(outcome.report_path), error=outcome.error)
    return ReadinessResult(
        ran=True,
        report_path=str(outcome.report_path),
        findings=len(outcome.report.findings),
        high=sum(1 for f in outcome.report.findings if f.severity == "high"),
    )


def readiness_payload(result: ReadinessResult) -> dict[str, object]:
    return {
        "report": result.report_path,
        "findings": result.findings,
        "high": result.high,
        "error": result.error,
    }
