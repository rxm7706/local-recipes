#!/usr/bin/env python3
"""bmad_drift_check.py — keep the local-recipes BMAD project docs in sync with the live factory.

The `_bmad-output/projects/local-recipes/` artifacts (planning AND implementation) hard-code
volatile facts about the conda-forge-expert factory (skill version, cf_atlas schema, MCP tool
count, atlas phase count, pixi env count, gotcha range) and follow filing conventions
(sprint-change-proposals in change-history/, retros in retros/). The factory ships a release
every few days, so these drift. This tool makes the drift visible instead of silent, and can
auto-fix the safe mechanical classes.

Checks (across planning-artifacts/ + implementation-artifacts/):
  pin-missing      a tracked doc has a missing/corrupt source_pin (breaks the drift contract)   [HARD]
  archive-misplaced a sprint-change-proposal / retro sits at the dir top level, not its subdir   [HARD, fixable]
  stray-file       a throwaway artifact (.patch/.diff/.bak/.orig/.tmp) in implementation-artifacts [HARD, fixable]
  spec-status-stale a spec-*.md still marked in-flight though a matching retro exists (it shipped) [DRIFT]
  pin-behind       a tracked doc's pinned skill MINOR is behind the live skill MINOR             [DRIFT]
  deferred-stale   deferred-work.md has no / a behind "Last reconciled" stamp                    [DRIFT]
  count-stale      a living doc states a schema/tool/phase count below the live value            [INFO]

Modes:
  --json / --groundtruth   print live ground-truth facts (machine-readable)
  --integrity-only         exit non-zero only on HARD findings (used by the meta-test; tolerates
                           docs that are merely a few releases behind between syncs)
  --fix                    perform the safe mechanical remediations (archive moves), then re-report
  (default)                full report; exit non-zero on any HARD or DRIFT finding

Pin gate = the repo's drift-detection contract: a doc re-syncs when the skill CHANGELOG MINOR
exceeds the doc's pin; PATCH bumps do not count as drift.

Usage:
  pixi run -e local-recipes bmad-drift-check
  pixi run -e local-recipes bmad-drift-check -- --fix
  pixi run -e local-recipes bmad-groundtruth
See _bmad-output/projects/local-recipes/SYNC-RUNBOOK.md for the full re-sync procedure.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL = REPO_ROOT / ".claude" / "skills" / "conda-forge-expert"
PROJ = REPO_ROOT / "_bmad-output" / "projects" / "local-recipes"
PLAN = PROJ / "planning-artifacts"
IMPL = PROJ / "implementation-artifacts"
BASELINE = PROJ / ".sync-baseline.json"  # records the repo state artifacts were last reconciled against
DOCS_SPECS = REPO_ROOT / "docs" / "specs"  # Tier-1: BMAD-consumable intake specs (bmad-quick-dev entry points)
IMPL_REL = "_bmad-output/projects/local-recipes/implementation-artifacts"

Ver = tuple[int, int, int]

# Tracked pinned docs and their sync category:
#   living   — must track the live factory; re-sync mechanically (counts) + bmad-index-docs.
#   context  — the agent spawn rulebook; re-sync via bmad-generate-project-context.
#   plan     — PRD/epics/readiness; structural re-sync via the bmad-correct-course chain.
#   snapshot — frozen dated record (e.g. a validation run); pin intentionally NOT current.
TRACKED: list[tuple[str, str]] = [
    ("planning-artifacts/index.md", "living"),
    ("planning-artifacts/architecture.md", "living"),
    ("planning-artifacts/architecture-cf-atlas.md", "living"),
    ("planning-artifacts/architecture-conda-forge-expert.md", "living"),
    ("planning-artifacts/architecture-mcp-server.md", "living"),
    ("planning-artifacts/architecture-bmad-infra.md", "living"),
    ("planning-artifacts/integration-architecture.md", "living"),
    ("planning-artifacts/development-guide.md", "living"),
    ("planning-artifacts/deployment-guide.md", "living"),
    ("planning-artifacts/source-tree-analysis.md", "living"),
    ("planning-artifacts/project-overview.md", "living"),
    ("planning-artifacts/project-parts.json", "living"),
    ("project-context.md", "context"),
    ("planning-artifacts/PRD.md", "plan"),
    ("planning-artifacts/epics.md", "plan"),
    ("planning-artifacts/implementation-readiness-report.md", "snapshot"),  # dated gate output, regenerated not pinned
    ("planning-artifacts/validation-report-PRD.md", "snapshot"),
]
TRACKED_CAT = dict(TRACKED)
TRACKED_REL = set(TRACKED_CAT)
CONFIG_FILES = {".bmad-config.toml"}            # config, not pin-synced — but must be accounted-for
IGNORE_PARTS = {"__pycache__"}

# Known-stale CONTENT patterns: claims wrong regardless of version, seeded by the deep agent
# audit (see SYNC-RUNBOOK.md). Grows like tests/meta/test_no_thirty_gb_lie.py over time.
STALE_RULE_PATTERNS: list[tuple[str, str]] = [
    (r"<recipe-name>-<version>",
     "stale branch-naming rule — CFE convention is add-recipe-<name> (auto-memory)"),
]

STRAY_SUFFIXES = {".patch", ".diff", ".bak", ".orig", ".tmp", ".rej"}
NONTERMINAL_STATUS = re.compile(r"\b(in[-\s]?flight|in[-\s]?progress|wip|pending|draft)\b", re.I)
TERMINAL_STATUS = re.compile(r"\b(done|shipped|complete|completed|cancelled|canceled|merged)\b", re.I)

HARD, DRIFT, INFO = "HARD", "DRIFT", "INFO"

_PIN_RE = re.compile(
    r"(?:source_pin|last_synced_skill_version)[\"']?\s*:\s*"  # tolerate JSON's quoted key
    r"['\"]?(?:conda-forge-expert\s+)?v?(\d+)\.(\d+)\.(\d+)",
)
_VER_RE = re.compile(r"\*\*v(\d+)\.(\d+)\.(\d+)\*\*")


class Finding:
    def __init__(self, severity: str, kind: str, target: str, detail: str, fixable: bool = False):
        self.severity, self.kind, self.target, self.detail, self.fixable = (
            severity, kind, target, detail, fixable)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _rel(path: Path) -> str:
    try:
        return path.relative_to(PROJ).as_posix()
    except ValueError:
        return str(path)


def _parse_ver(s: str | None) -> Ver:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)


# ---------------------------------------------------------------- ground truth
def skill_version() -> str | None:
    m = _VER_RE.search(_read(SKILL / "CHANGELOG.md"))
    return f"{m.group(1)}.{m.group(2)}.{m.group(3)}" if m else None


def schema_version() -> int | None:
    m = re.search(r"SCHEMA_VERSION\s*=\s*(\d+)", _read(SKILL / "scripts" / "conda_forge_atlas.py"))
    return int(m.group(1)) if m else None


def mcp_tool_count() -> int:
    return _read(REPO_ROOT / ".claude" / "tools" / "conda_forge_server.py").count("@mcp.tool")


def phase_count() -> int:
    return len(re.findall(r"^\s*def phase_", _read(SKILL / "scripts" / "conda_forge_atlas.py"), re.M))


def phase_ids() -> list[str]:
    """Top-level + sub phase IDs from the PHASES registry, e.g. ['B','B.5',...,'O','P',...]."""
    text = _read(SKILL / "scripts" / "conda_forge_atlas.py")
    m = re.search(r"PHASES\s*[:=].*?\[(.*?)\n\]", text, re.S)
    return re.findall(r'\(\s*"([^"]+)"', m.group(1)) if m else []


def max_single_phase() -> str:
    singles = [p for p in phase_ids() if re.fullmatch(r"[A-Z]", p)]
    return max(singles) if singles else "N"


def gotcha_max() -> int | None:
    nums = [int(n) for n in re.findall(r"^###\s+G(\d+)", _read(SKILL / "SKILL.md"), re.M)]
    return max(nums) if nums else None


def env_count() -> int:
    out, in_block = 0, False
    for line in _read(REPO_ROOT / "pixi.toml").splitlines():
        if line.strip() == "[environments]":
            in_block = True
            continue
        if in_block:
            if line.startswith("["):
                break
            if "=" in line and not line.lstrip().startswith("#"):
                out += 1
    return out


def recipe_split() -> dict[str, int]:
    # Churny: changes constantly during the v0->v1 migration. Informational only, never gated.
    recipes = REPO_ROOT / "recipes"
    if not recipes.is_dir():
        return {"dirs": 0, "recipe_yaml": 0, "meta_yaml": 0}
    return {
        "dirs": len([p for p in recipes.iterdir() if p.is_dir()]),
        "recipe_yaml": len(list(recipes.glob("*/recipe.yaml"))),
        "meta_yaml": len(list(recipes.glob("*/meta.yaml"))),
    }


def ground_truth() -> dict:
    return {
        "skill_version": skill_version(),
        "schema_version": schema_version(),
        "mcp_tools": mcp_tool_count(),
        "atlas_phases": phase_count(),
        "gotcha_max": gotcha_max(),
        "pixi_envs": env_count(),
        "recipes_churny": recipe_split(),
    }


# -------------------------------------------------------------- sync baseline
# The baseline is the closed-loop anchor: it records the source-of-truth SURFACE the artifacts
# were last reconciled against, so the detector trips on ANY out-of-band change (BMAD or not),
# not just the specific counts the checks hardcode.
FINGERPRINT_KEYS = ("skill_version", "schema_version", "mcp_tools", "atlas_phases",
                    "gotcha_max", "pixi_envs", "phase_ids")


def git_head() -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or None
    except Exception:
        return None


def git_tracked(relpath: str) -> list[str]:
    """Files git is tracking under relpath (repo-relative). Empty on error."""
    try:
        r = subprocess.run(["git", "-C", str(REPO_ROOT), "ls-files", "--", relpath],
                           capture_output=True, text=True, timeout=15)
        return [ln for ln in r.stdout.splitlines() if ln.strip()]
    except Exception:
        return []


def fingerprint() -> dict:
    gt = ground_truth()
    fp = {k: gt[k] for k in FINGERPRINT_KEYS if k in gt}
    fp["phase_ids"] = phase_ids()
    fp["git_head"] = git_head()
    return fp


def check_baseline() -> list[Finding]:
    if not BASELINE.is_file():
        return [Finding(INFO, "no-baseline", ".sync-baseline.json",
                        "no reconciliation baseline — run `bmad-drift-check -- --write-baseline` after a sync")]
    try:
        base = json.loads(_read(BASELINE))
    except (ValueError, OSError):
        return [Finding(HARD, "baseline-corrupt", ".sync-baseline.json", "cannot parse baseline JSON")]
    live, out = fingerprint(), []
    for k in FINGERPRINT_KEYS:
        if base.get(k) != live.get(k):
            out.append(Finding(DRIFT, "surface-changed", k,
                               f"{k}: baseline {base.get(k)} -> live {live.get(k)} "
                               f"(out-of-band change since git {base.get('git_head')})"))
    return out


# ----------------------------------------------------------------- doc parsing
def doc_pin(path: Path) -> Ver | None:
    """Return (major, minor, patch) from the frontmatter pin, or None if absent/corrupt."""
    text = _read(path)
    if not text:
        return None
    if path.suffix == ".json":
        scope = text  # JSON has no frontmatter fence; scan the whole (small) file.
    else:
        parts = text.split("---", 2)  # only the frontmatter, so we skip pins quoted in prose
        scope = parts[1] if len(parts) >= 3 and text.lstrip().startswith("---") else text[:1500]
    m = _PIN_RE.search(scope)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def _spec_status(text: str) -> str | None:
    # frontmatter `status:` or a `**Status:**` line near the top
    m = re.search(r"^status\s*:\s*(.+)$", text[:2000], re.M | re.I)
    if not m:
        m = re.search(r"\*\*status\*\*\s*:?\s*(.+)$", text[:2000], re.M | re.I)
    return m.group(1).strip() if m else None


def frontmatter_status(path: Path) -> str | None:
    """The neutral `status:` from a spec's YAML frontmatter (framework-agnostic source of truth)."""
    text = _read(path)
    parts = text.split("---", 2)
    fm = parts[1] if len(parts) >= 3 and text.lstrip().startswith("---") else text[:600]
    m = re.search(r"^\s*status\s*:\s*([A-Za-z-]+)", fm, re.M)
    return m.group(1).lower() if m else None


def _slug(name: str) -> str:
    s = re.sub(r"\.md$", "", name)
    s = re.sub(r"^(spec|retro)-", "", s)
    s = re.sub(r"-v?\d+\.\d+\.\d+", "", s)
    s = re.sub(r"-\d{4}-\d{2}-\d{2}", "", s)
    return s.strip("-")


# --------------------------------------------------------------------- checks
def check_pins(live: Ver) -> list[Finding]:
    out = []
    for rel, cat in TRACKED:
        pin = doc_pin(PROJ / rel)
        if pin is None:
            if cat != "snapshot":
                out.append(Finding(HARD, "pin-missing", rel,
                                   "missing/corrupt source_pin — breaks the drift contract"))
        elif (pin[0], pin[1]) < (live[0], live[1]):
            sev = INFO if cat == "snapshot" else DRIFT
            out.append(Finding(sev, "pin-behind", rel,
                               f"pinned v{pin[0]}.{pin[1]}.{pin[2]} < live v{live[0]}.{live[1]}.{live[2]} [{cat}]"))
    return out


def check_archive_hygiene() -> list[Finding]:
    out = []
    if PLAN.is_dir():
        for p in PLAN.glob("sprint-change-proposal-*.md"):
            out.append(Finding(HARD, "archive-misplaced", f"planning-artifacts/{p.name}",
                               "sprint-change-proposal belongs in change-history/", fixable=True))
    if IMPL.is_dir():
        for p in IMPL.glob("retro-*.md"):
            out.append(Finding(HARD, "archive-misplaced", f"implementation-artifacts/{p.name}",
                               "retro belongs in retros/", fixable=True))
        for p in IMPL.iterdir():
            if p.is_file() and p.suffix in STRAY_SUFFIXES:
                out.append(Finding(HARD, "stray-file", f"implementation-artifacts/{p.name}",
                                   "throwaway artifact (already in git history) — remove", fixable=True))
    return out


def check_spec_status() -> list[Finding]:
    out = []
    if not IMPL.is_dir():
        return out
    retro_slugs = []
    retros_dir = IMPL / "retros"
    if retros_dir.is_dir():
        retro_slugs = [_slug(p.name) for p in retros_dir.glob("retro-*.md")]
    for spec in IMPL.glob("spec-*.md"):
        status = _spec_status(_read(spec))
        if not status or TERMINAL_STATUS.search(status) or not NONTERMINAL_STATUS.search(status):
            continue
        sslug = _slug(spec.name)
        shipped = any(sslug and (sslug in rs or rs in sslug) for rs in retro_slugs)
        if shipped:
            out.append(Finding(DRIFT, "spec-status-stale", f"implementation-artifacts/{spec.name}",
                               f"status '{status}' but a matching retro exists — it shipped"))
    return out


def check_deferred_work(live: Ver) -> list[Finding]:
    df = IMPL / "deferred-work.md"
    if not df.is_file():
        return []
    text = _read(df)
    m = re.search(r"last\s+reconciled[^\n]*?v(\d+)\.(\d+)\.(\d+)", text, re.I)
    if not m:
        return [Finding(DRIFT, "deferred-stale", "implementation-artifacts/deferred-work.md",
                        "no 'Last reconciled: ... vX.Y.Z' stamp — cannot tell if it is current")]
    pin = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if (pin[0], pin[1]) < (live[0], live[1]):
        return [Finding(DRIFT, "deferred-stale", "implementation-artifacts/deferred-work.md",
                        f"reconciled at v{pin[0]}.{pin[1]}.{pin[2]} < live v{live[0]}.{live[1]}.{live[2]}")]
    return []


def check_counts(gt: dict) -> list[Finding]:
    # Heuristic, INFO only: flag a living doc that states a schema/tool/phase number below live.
    out = []
    probes = [
        (r"schema v(\d+)\b", gt["schema_version"], "schema"),
        (r"(\d+)\s+MCP tools", gt["mcp_tools"], "MCP tools"),
        (r"G1[–-]G(\d+)", gt["gotcha_max"], "gotcha range"),
        (r"(\d+)\s+pixi envs", gt["pixi_envs"], "pixi envs"),
    ]
    for rel, cat in TRACKED:
        if cat != "living":
            continue
        text = _read(PROJ / rel)
        for pat, live_val, label in probes:
            if live_val is None:
                continue
            for mm in re.finditer(pat, text):
                if int(mm.group(1)) < live_val:
                    out.append(Finding(INFO, "count-stale", rel,
                                       f"states {label} {mm.group(1)} < live {live_val} (review in context)"))
                    break
    return out


def check_stale_rules() -> list[Finding]:
    # Known-wrong content strings (branch convention, etc.) anywhere in the project docs.
    out = []
    if not PROJ.is_dir():
        return out
    for path in PROJ.rglob("*.md"):
        if any(p in IGNORE_PARTS for p in path.parts):
            continue
        text = _read(path)
        for pat, why in STALE_RULE_PATTERNS:
            if re.search(pat, text):
                out.append(Finding(DRIFT, "stale-rule", _rel(path), why))
    return out


def check_phase_lists() -> list[Finding]:
    # A doc that enumerates atlas phases as a B/.../N slash-list must extend to the live max phase.
    out, hi = [], max_single_phase()
    for rel, cat in TRACKED:
        if cat == "snapshot":
            continue
        for m in re.finditer(r"\bB(?:/[A-Z](?:\.\d)?'?){4,}", _read(PROJ / rel)):
            seg = m.group(0)
            if "/C/" not in seg or "/D" not in seg:
                continue  # illustrative subset (e.g. "B/F/H/K/N/..."), not the full enumeration
            if f"/{hi}" not in seg and not seg.endswith(hi):
                out.append(Finding(DRIFT, "phase-list-stale", rel,
                                   f"atlas-phase list '{seg[:32]}…' omits phases through {hi}"))
                break
    return out


def classify(path: Path) -> str:
    rel = _rel(path)
    if any(part in IGNORE_PARTS for part in path.parts):
        return "ignored"
    if rel in CONFIG_FILES:
        return "config"
    if rel == ".sync-baseline.json":
        return "baseline"
    if rel == "SYNC-RUNBOOK.md":
        return "runbook"
    if rel == "project-context.md":
        return "tracked:context"
    if rel in TRACKED_REL:
        return f"tracked:{TRACKED_CAT[rel]}"
    if rel.startswith("planning-artifacts/change-history/"):
        return "archive:change-history"
    if rel.startswith("implementation-artifacts/retros/"):
        return "archive:retros"
    if rel == "implementation-artifacts/deferred-work.md":
        return "tracked:deferred"
    if re.fullmatch(r"implementation-artifacts/spec-.*\.md", rel):
        return "tracked:spec"
    return "UNKNOWN"


def check_coverage() -> tuple[list[Finding], dict[str, int]]:
    """Walk the whole project; HARD-fail any file no rule classifies — so coverage can't lapse."""
    findings: list[Finding] = []
    summary: dict[str, int] = {}
    if not PROJ.is_dir():
        return findings, summary
    for path in sorted(PROJ.rglob("*")):
        if not path.is_file():
            continue
        cls = classify(path)
        if cls == "ignored":
            continue
        summary[cls] = summary.get(cls, 0) + 1
        if cls == "UNKNOWN" and path.suffix not in STRAY_SUFFIXES:  # strays handled elsewhere
            findings.append(Finding(HARD, "uncovered", _rel(path),
                                   "not covered by drift-check — add a classification rule"))
    if DOCS_SPECS.is_dir():  # Tier-1 intake specs (repo-root, outside the project tree)
        summary["intake:docs-specs"] = len(list(DOCS_SPECS.glob("*.md")))
    return findings, summary


def check_tier_alignment() -> list[Finding]:
    """Enforce the BMAD-method tier model:
      Tier-1 intake specs -> docs/specs/ (neutral, tracked)
      Tier-3 execution    -> implementation-artifacts/ (gitignored, local-only)
    So a git-tracked file under implementation-artifacts/ is misfiled (an intake spec that
    belongs in docs/specs/, or a Tier-3 output that should not be committed)."""
    out = []
    for f in git_tracked(IMPL_REL):
        name = f.rsplit("/", 1)[-1]
        remedy = ("intake spec -> git mv to docs/specs/" if name.startswith("spec-")
                  else "Tier-3 output -> keep local (git rm --cached)")
        out.append(Finding(HARD, "tracked-impl-artifact", f,
                           f"implementation-artifacts is gitignored/local-only; this file is "
                           f"git-tracked ({remedy})"))
    if DOCS_SPECS.is_dir():
        for p in sorted(DOCS_SPECS.iterdir()):
            if p.is_file() and p.suffix != ".md":
                out.append(Finding(DRIFT, "docs-specs-nonmd", f"docs/specs/{p.name}",
                                   "docs/specs holds BMAD intake specs (markdown) — non-.md is misfiled"))
    return out


def check_spec_indexed() -> list[Finding]:
    """Every Tier-1 intake spec must be referenced in CLAUDE.md's Project Documentation Reference,
    so the human/agent index stays complete as specs are added."""
    if not DOCS_SPECS.is_dir():
        return []
    claude = _read(REPO_ROOT / "CLAUDE.md")
    return [Finding(DRIFT, "spec-unindexed", f"docs/specs/{p.name}",
                    "not referenced in CLAUDE.md Project Documentation Reference")
            for p in sorted(DOCS_SPECS.glob("*.md")) if p.name not in claude]


def run_checks() -> tuple[list[Finding], dict, dict[str, int]]:
    gt = ground_truth()
    live = _parse_ver(gt["skill_version"])
    cov_findings, coverage = check_coverage()
    findings = (check_pins(live) + check_archive_hygiene() + check_spec_status()
                + check_deferred_work(live) + check_counts(gt) + check_stale_rules()
                + check_phase_lists() + check_baseline() + check_tier_alignment()
                + check_spec_indexed() + cov_findings)
    return findings, gt, coverage


# ----------------------------------------------------------------------- fix
def do_fix() -> list[str]:
    actions = []
    if PLAN.is_dir():
        misplaced = list(PLAN.glob("sprint-change-proposal-*.md"))
        if misplaced:
            (PLAN / "change-history").mkdir(exist_ok=True)
            for p in misplaced:
                p.rename(PLAN / "change-history" / p.name)
                actions.append(f"moved {p.name} -> change-history/")
    if IMPL.is_dir():
        retros = list(IMPL.glob("retro-*.md"))
        if retros:
            (IMPL / "retros").mkdir(exist_ok=True)
            for p in retros:
                p.rename(IMPL / "retros" / p.name)
                actions.append(f"moved {p.name} -> retros/")
        for p in list(IMPL.iterdir()):
            if p.is_file() and p.suffix in STRAY_SUFFIXES:
                p.unlink()
                actions.append(f"removed stray {p.name}")
    return actions


# --------------------------------------------------------------------- output
def cmd_json() -> int:
    print(json.dumps(ground_truth(), indent=2))
    return 0


def cmd_specs() -> int:
    """Report each Tier-1 intake spec's neutral status + whether it's indexed in CLAUDE.md."""
    if not DOCS_SPECS.is_dir():
        print(f"no docs/specs/ at {DOCS_SPECS}", file=sys.stderr)
        return 0
    claude = _read(REPO_ROOT / "CLAUDE.md")
    specs = sorted(DOCS_SPECS.glob("*.md"))
    w = max((len(p.name) for p in specs), default=4)
    print(f"docs/specs intake specs ({len(specs)}) — status is the framework-neutral source of truth\n")
    print(f"  {'SPEC'.ljust(w)}  {'STATUS':<12} INDEXED")
    print(f"  {'-' * w}  {'-' * 12} -------")
    by_status: dict[str, int] = {}
    for p in specs:
        st = frontmatter_status(p) or "(none)"
        by_status[st] = by_status.get(st, 0) + 1
        print(f"  {p.name.ljust(w)}  {st:<12} {'yes' if p.name in claude else 'NO'}")
    print("\n  totals: " + "  ".join(f"{k}={v}" for k, v in sorted(by_status.items())))
    return 0


def _print_report(findings: list[Finding], gt: dict, coverage: dict[str, int]) -> None:
    live = gt["skill_version"]
    rc = gt["recipes_churny"]
    print(f"BMAD project drift — live conda-forge-expert v{live}\n")
    print(f"  schema v{gt['schema_version']} | {gt['mcp_tools']} MCP tools | "
          f"{gt['atlas_phases']} phases | {gt['pixi_envs']} pixi envs | G1-G{gt['gotcha_max']}")
    print(f"  recipes (churny, not gated): {rc['dirs']} dirs = "
          f"{rc['recipe_yaml']} recipe.yaml + {rc['meta_yaml']} meta.yaml")
    total = sum(coverage.values())
    cov = "  ".join(f"{k}={v}" for k, v in sorted(coverage.items()))
    print(f"\n  coverage: {total} files classified — {cov}\n")
    if not findings:
        print("  (no findings)")
        return
    for sev in (HARD, DRIFT, INFO):
        group = [f for f in findings if f.severity == sev]
        if not group:
            continue
        print(f"  {sev} ({len(group)}):")
        for f in group:
            tag = " [auto-fixable]" if f.fixable else ""
            print(f"    - [{f.kind}] {f.target}: {f.detail}{tag}")
        print()


def cmd_check(integrity_only: bool, fix: bool) -> int:
    if fix:
        actions = do_fix()
        print("FIX applied:" if actions else "FIX: nothing to remediate.")
        for a in actions:
            print(f"  - {a}")
        print()
    findings, gt, coverage = run_checks()
    _print_report(findings, gt, coverage)
    hard = [f for f in findings if f.severity == HARD]
    drift = [f for f in findings if f.severity == DRIFT]
    if integrity_only:
        if hard:
            print(f"FAIL: {len(hard)} integrity issue(s). See SYNC-RUNBOOK.md "
                  f"(some are auto-fixable: bmad-drift-check -- --fix).")
            return 1
        print("OK: integrity clean (every tracked doc has a pin; filing conventions respected).")
        return 0
    if hard or drift:
        fixable = [f for f in findings if f.fixable]
        hint = "  (run with --fix to auto-remediate the mechanical ones)" if fixable else ""
        print(f"DRIFT: {len(hard)} integrity + {len(drift)} currency finding(s). "
              f"Re-sync via _bmad-output/projects/local-recipes/SYNC-RUNBOOK.md.{hint}")
        return 1
    print("OK: all tracked BMAD artifacts are in sync with the live factory MINOR.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check BMAD project-doc drift vs the live factory.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--json", "--groundtruth", action="store_true", dest="json",
                   help="print live ground-truth facts as JSON")
    g.add_argument("--integrity-only", action="store_true",
                   help="fail only on HARD findings (for the meta-test)")
    g.add_argument("--specs", action="store_true",
                   help="report each docs/specs intake spec's status + CLAUDE.md index state")
    ap.add_argument("--fix", action="store_true",
                    help="apply safe mechanical remediations (archive moves, stray-file removal)")
    ap.add_argument("--write-baseline", action="store_true",
                    help="stamp .sync-baseline.json to the current state (run after a reconciliation)")
    args = ap.parse_args(argv)
    if not PROJ.is_dir():
        print(f"BMAD project not found at {PROJ} — nothing to check.", file=sys.stderr)
        return 0
    if args.json:
        return cmd_json()
    if args.specs:
        return cmd_specs()
    if args.write_baseline:
        BASELINE.write_text(json.dumps(fingerprint(), indent=2) + "\n", encoding="utf-8")
        fp = fingerprint()
        print(f"baseline written: {_rel(BASELINE)} @ git {fp.get('git_head')} / skill v{fp.get('skill_version')}")
        return 0
    return cmd_check(integrity_only=args.integrity_only, fix=args.fix)


if __name__ == "__main__":
    raise SystemExit(main())
