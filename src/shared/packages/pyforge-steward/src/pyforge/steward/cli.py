"""Steward's dispatcher — and the sole owner of the process exit code (AD-8).

``main()`` catches every way a duty can end and **projects** it to a documented
code. It never trusts a ``SystemExit`` raised inside a duty verbatim, and it
never lets an unexpected exception fall through to the interpreter's bare ``1``
— an undocumented ``1`` is indistinguishable from a duty that legitimately
failed, which is exactly the false signal a gate must not emit.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from . import __version__
from .interfaces import Duty, DutyResult, NullDuty

EXIT_OK = 0
EXIT_FAILED = 1          # a duty ran and reported ok=False — the ONLY legitimate 1
EXIT_USAGE = 2           # argparse convention
EXIT_INTERRUPTED = 130   # 128 + SIGINT
EXIT_INTERNAL = 70       # EX_SOFTWARE — a crash, never conflated with EXIT_FAILED

# budget's own triad (AD-6, FR-18): "no metered spend source configured" is
# the ONLY one implemented in v1 (no metering source exists — see budget.py's
# module docstring) — 0 (EXIT_OK) and EXIT_FAILED remain reserved for a
# FUTURE "under budget"/"over budget" comparison a later story would add
# once a real metered spend source exists; nothing in v1 ever returns those
# two codes FROM `budget check` specifically. `3` is picked simply because
# it is the next unused small integer after EXIT_USAGE(2) — not itself
# meaningful, just distinct and documented.
EXIT_BUDGET_NOT_CONFIGURED = 3

# The eight duties — all real as of this story. `keys` (Epic 1), `deploy`
# (Epic 2), `provision` (Epic 3), `budget` (Epic 4, complete as of Story 4.3),
# `sync` (Epic 8, Story 8.1), `workspace` (Epic 13, Stories 13.1–13.2),
# `upgrade` (Epic 14, Stories 14.1–14.5 — pre-flight + apply + CAP-3 reconcile + CAP-4 pin fan-out + CAP-5 prove-landed),
# `suite` (Epic 15, Story 15.1 — CAP-1 pipeline-truth report).
DUTIES: tuple[str, ...] = (
    "keys", "deploy", "provision", "budget", "sync", "workspace", "upgrade", "suite",
)

_HELP = {
    "keys": "credential lifecycle — encrypt/decrypt/rotate/list/audit/revoke",
    "deploy": (
        "dashboard build/reconcile/status; perimeter: AD-5 shareability + daphne/nginx "
        "manifests; static: CAP-8/AD-10 static-export publish"
    ),
    "provision": "environment and substrate provisioning",
    "budget": "cost budgeting and enforcement",
    "sync": "bidirectional GitHub Projects V2 <-> Jira Cloud reconciliation",
    "workspace": (
        "story-scoped scratch worktrees — start/ls/status/clean "
        "(single-repo or repo-set; own-worktrees-only; archive-not-delete)"
    ),
    "upgrade": (
        "BMAD-METHOD core upgrade — bmad-core pre-flight (CAP-1), "
        "deliberate --apply (CAP-2), CAP-3 clobber detect/re-apply, "
        "pin-fan-out report (CAP-4), prove-landed single verdict (CAP-5); "
        "never edits foreign-station pin sites beyond documented loop-home "
        "relay refresh"
    ),
    "suite": (
        "bmad-suite channel product — pipeline-truth (CAP-1) reports "
        "upstream/recipe/channel/installed/wired for all 13 suite packages "
        "with per-stage drift and fail-open probes; advance (CAP-2) chains "
        "autotick→build→test→publish→listing→reviewable PR (never auto-merged)"
    ),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="steward",
        description="Steward — the Provisioner's station.",
    )
    parser.add_argument("--version", action="version", version=f"steward {__version__}")
    subs = parser.add_subparsers(dest="duty", metavar="{" + ",".join(DUTIES) + "}")
    for name in DUTIES:
        duty_parser = subs.add_parser(name, help=_HELP[name], description=_HELP[name])
        if name == "keys":
            _add_keys_subparsers(duty_parser)
        elif name == "deploy":
            _add_deploy_subparsers(duty_parser)
        elif name == "provision":
            _add_provision_subparsers(duty_parser)
        elif name == "budget":
            _add_budget_subparsers(duty_parser)
        elif name == "sync":
            _add_sync_subparsers(duty_parser)
        elif name == "workspace":
            _add_workspace_subparsers(duty_parser)
        elif name == "upgrade":
            _add_upgrade_subparsers(duty_parser)
        elif name == "suite":
            _add_suite_subparsers(duty_parser)
    return parser


def _add_keys_subparsers(keys_parser: argparse.ArgumentParser) -> None:
    """Add `encrypt`/`decrypt` verbs (Story 1.3) — the only CLI surface this
    story adds. Flag names deliberately mirror `age`'s own (`--recipient`/
    `-r`, `--identity`/`-i`, `--output`/`-o`).
    """
    keys_subs = keys_parser.add_subparsers(
        dest="keys_verb", metavar="{encrypt,decrypt,rotate,list,audit,revoke}"
    )

    encrypt = keys_subs.add_parser("encrypt", help="age-encrypt a file to a recipient")
    encrypt.add_argument("file", help="the plaintext file to encrypt")
    encrypt.add_argument("--recipient", "-r", required=True, help="the age public key to encrypt to")
    encrypt.add_argument("--output", "-o", required=True, help="path to write the encrypted file")

    decrypt = keys_subs.add_parser("decrypt", help="age-decrypt a file with an identity")
    decrypt.add_argument("file", help="the age-encrypted file to decrypt")
    decrypt.add_argument("--identity", "-i", required=True, help="the age identity (secret key) file")
    decrypt.add_argument("--output", "-o", required=True, help="path to write the decrypted file")

    rotate = keys_subs.add_parser(
        "rotate", help="rotate an issued identity, re-encrypting every secret it protects"
    )
    rotate.add_argument("--scope", required=True, help="the credential scope to rotate")
    rotate.add_argument(
        "--new-identity", required=True, help="path to write the newly generated age identity"
    )
    rotate.add_argument(
        "--inventory",
        default=None,
        help="path to keys-inventory.yaml (default: repo-root .steward/keys-inventory.yaml)",
    )

    list_ = keys_subs.add_parser("list", help="list known credential identities (never a secret value)")
    list_.add_argument(
        "--inventory",
        default=None,
        help="path to keys-inventory.yaml (default: repo-root .steward/keys-inventory.yaml)",
    )
    list_.add_argument("--json", action="store_true", help="emit JSON instead of a text table")

    audit = keys_subs.add_parser(
        "audit", help="scan for host-unscoped credential attachment and/or plaintext secrets"
    )
    audit.add_argument(
        "--drift", action="store_true", help="scan for the historical host-unscoped-attachment shape"
    )
    audit.add_argument(
        "--path",
        default=None,
        help="file to scan for --drift (default: the _http.py delegate module)",
    )
    audit.add_argument(
        "--secrets",
        default=None,
        metavar="PATH",
        help="file or directory to scan for plaintext-secret-shaped content",
    )

    revoke = keys_subs.add_parser(
        "revoke", help="mark a credential retired and print manual remediation guidance"
    )
    revoke.add_argument("--scope", required=True, help="the credential scope to revoke")
    revoke.add_argument(
        "--inventory",
        default=None,
        help="path to keys-inventory.yaml (default: repo-root .steward/keys-inventory.yaml)",
    )


def _add_deploy_subparsers(deploy_parser: argparse.ArgumentParser) -> None:
    """Add the `dashboard` (`--build`/`--dry-run`), `status`, `perimeter`,
    and `static` verbs. `perimeter` is a distinct, unrelated surface from
    `dashboard` (Story 9.5, CAP-6) — it validates and renders the
    `pyforge.steward.dashboard` Django app's deployment perimeter (AD-5
    shareability + daphne/nginx manifests), never the GitHub-Pages program
    console `dashboard` builds/reconciles. `static` (Story 9.7, CAP-8/
    AD-10) publishes a board as a self-contained static export to
    `docs/dashboard/<board>/index.html`, which the pre-existing `dashboard`
    verb then commits/pushes unchanged — a fourth, also-unrelated surface.
    """
    deploy_subs = deploy_parser.add_subparsers(
        dest="deploy_verb", metavar="{dashboard,status,perimeter,static}"
    )

    dashboard = deploy_subs.add_parser(
        "dashboard", help="build/reconcile the GitHub Pages program-console dashboard"
    )
    dashboard.add_argument(
        "--build", action="store_true", help="build only — refresh docs/dashboard/, no diff/commit/push"
    )
    dashboard.add_argument(
        "--dry-run", action="store_true", help="build + diff and print — no commit/push"
    )

    deploy_subs.add_parser(
        "status", help="report the last commit that touched docs/dashboard/ (SHA, timestamp)"
    )

    perimeter = deploy_subs.add_parser(
        "perimeter",
        help=(
            "validate the AD-5 cross-worker shareability of a dashboard "
            "deployment topology and render its daphne+nginx manifests (CAP-6)"
        ),
    )
    perimeter.add_argument(
        "--workers",
        type=int,
        default=1,
        metavar="N",
        help="daphne worker count (default: 1 — a single worker may use in-process backends, AD-5)",
    )
    perimeter.add_argument(
        "--cache-backend",
        default="django.core.cache.backends.locmem.LocMemCache",
        metavar="DOTTED_PATH",
        help=(
            "dotted class path an adopter's Django CACHES setting would name "
            "(default: LocMemCache — single-worker only)"
        ),
    )
    perimeter.add_argument(
        "--channel-layer-backend",
        default="channels.layers.InMemoryChannelLayer",
        metavar="DOTTED_PATH",
        help=(
            "dotted class path an adopter's Django CHANNEL_LAYERS setting "
            "would name (default: InMemoryChannelLayer — single-worker only)"
        ),
    )
    perimeter.add_argument(
        "--trusted-address",
        action="append",
        metavar="ADDR",
        help="a trusted ingress peer address (repeatable) — required together with --output-dir",
    )
    perimeter.add_argument(
        "--tls-cert", metavar="PATH", help="path to the TLS certificate — required together with --output-dir"
    )
    perimeter.add_argument(
        "--tls-key", metavar="PATH", help="path to the TLS private key — required together with --output-dir"
    )
    perimeter.add_argument(
        "--output-dir",
        metavar="DIR",
        help="write the rendered daphne unit + nginx edge config here (omit for validation-only)",
    )

    static = deploy_subs.add_parser(
        "static",
        help=(
            "publish a board as a self-contained static export "
            "(docs/dashboard/<board>/index.html) — CAP-8/AD-10"
        ),
    )
    static.add_argument(
        "--board",
        required=True,
        metavar="SLUG",
        help=(
            "the board slug (filesystem-safe: ^[A-Za-z0-9_-]+$; also refused when "
            "docs/dashboard/<slug>/ is excluded by a .gitignore rule, since such a "
            "board could never be committed or pushed)"
        ),
    )
    static.add_argument(
        "--panel",
        action="append",
        metavar="LABEL=PATH",
        help="a pre-rendered HTML panel to embed verbatim (repeatable, in call order)",
    )
    static.add_argument(
        "--access-column",
        default=None,
        metavar="NAME",
        help=(
            "the board's declared access column, if any — refuses (AD-10) rather than "
            "publishing, since static export cannot honor row-level access"
        ),
    )


def _add_provision_subparsers(provision_parser: argparse.ArgumentParser) -> None:
    """Add the `--list-modules`/`--module`/`--env`/`--runner`/`--list`/
    `--json`/`--verify` flags (Epic 3's four stories, plus Epic 6 Story
    6.1's `--module` and Story 6.2's `--list-modules`).

    Unlike `keys`/`deploy`, `provision` has no verb subcommands — every
    action is a flag directly on the `provision` duty parser, matching each
    story's own `steward provision --list-modules [--json]` / `--module
    <name> [--json]` / `--env <name>` / `--runner bmad-loop --env <name>` /
    `--list [--json]` / `--verify` shape verbatim.
    """
    # Keep "supported: ..." in sync with provision.py's `_SUPPORTED_MODULES`
    # (that module is deliberately not imported here -- see its own comment).
    provision_parser.add_argument(
        "--list-modules",
        action="store_true",
        help="list every registered module with installed/available state (derived from the filesystem)",
    )
    provision_parser.add_argument(
        "--module", metavar="NAME", help="BMAD module to provision (supported: bmb)"
    )
    provision_parser.add_argument(
        "--env", metavar="NAME", help="pixi environment name (pixi.toml's [environments] table)"
    )
    provision_parser.add_argument(
        "--runner",
        choices=["bmad-loop"],
        help="materialize a runner's worktree together with --env (Story 3.2)",
    )
    provision_parser.add_argument(
        "--list", action="store_true", help="list every environment in pixi.toml's [environments] table"
    )
    provision_parser.add_argument(
        "--json",
        action="store_true",
        help="with --list, --module, or --list-modules, emit JSON instead of text",
    )
    provision_parser.add_argument(
        "--verify", action="store_true", help="check environment.yaml against pixi.toml (the PR CI sync gate)"
    )


def _add_budget_subparsers(budget_parser: argparse.ArgumentParser) -> None:
    """Add the `set`/`show`/`check` verbs (Epic 4, all three stories)."""
    budget_subs = budget_parser.add_subparsers(dest="budget_verb", metavar="{set,show,check}")

    set_ = budget_subs.add_parser("set", help="declare a machine-readable budget ceiling")
    set_.add_argument(
        "--cap", required=True, help="<amount><currency>/<period>, e.g. '1500usd/month'"
    )

    show = budget_subs.add_parser("show", help="print the currently declared ceiling(s)")
    show.add_argument("--json", action="store_true", help="emit JSON instead of human-readable text")

    budget_subs.add_parser(
        "check", help="report whether spend is under the declared ceiling (v1: honest 'no data' only)"
    )


def _add_sync_subparsers(sync_parser: argparse.ArgumentParser) -> None:
    """Add the `reconcile` verb (Epic 8, Story 8.1) — the only verb this
    story defines. `--github-item`/`--jira-issue`/`--schedule` are mutually
    exclusive and one is required: `reconcile` resolves whichever identifier
    wasn't given via the other side's link field (see `sync.py`'s
    `reconcile` docstring); `--schedule` (Story 8.4, `trigger=schedule`,
    AD-1's default operating mode) instead bulk-enumerates every linked item
    on the board and reconciles each in one run (`sync.py`'s
    `reconcile_schedule_batch`).
    """
    sync_subs = sync_parser.add_subparsers(dest="sync_verb", metavar="{reconcile}")

    reconcile_ = sync_subs.add_parser(
        "reconcile", help="re-read both linked items and converge the divergent side"
    )
    identifier_group = reconcile_.add_mutually_exclusive_group(required=True)
    identifier_group.add_argument(
        "--github-item", metavar="ID", help="GitHub Projects V2 item node ID"
    )
    identifier_group.add_argument("--jira-issue", metavar="KEY", help="Jira issue key")
    identifier_group.add_argument(
        "--schedule",
        action="store_true",
        help=(
            "trigger=schedule: bulk-enumerate every linked item on the GitHub Projects V2 "
            "board and reconcile each in this one run"
        ),
    )
    reconcile_.add_argument(
        "--config",
        default=None,
        metavar="PATH",
        help="path to sync-config.yaml (default: repo-root .steward/sync-config.yaml)",
    )
    reconcile_.add_argument(
        "--dry-run", action="store_true", help="compute and report the decision — make no write calls"
    )


def _add_workspace_subparsers(workspace_parser: argparse.ArgumentParser) -> None:
    """Add `start`/`ls`/`status`/`clean` (Stories 13.1–13.4 / CAP-1..4 + set teardown)."""
    workspace_subs = workspace_parser.add_subparsers(
        dest="workspace_verb", metavar="{start,ls,status,clean}"
    )

    start = workspace_subs.add_parser(
        "start", help="create a scratch worktree and record it in bookkeeping"
    )
    start.add_argument(
        "slug",
        help=(
            "story/task slug (single-repo branch name) or a repo-set feature "
            "slug from .steward/repo-sets.yaml projects.<slug>"
        ),
    )
    start.add_argument(
        "--from",
        dest="from_ref",
        default="origin/main",
        metavar="BRANCH",
        help="source ref to branch from (default: origin/main)",
    )
    start.add_argument("--json", action="store_true", help="emit JSON instead of the path")

    ls = workspace_subs.add_parser(
        "ls", help="list tool-created scratch worktrees (bookkeeping only; cheap)"
    )
    ls.add_argument("--json", action="store_true", help="emit JSON instead of a text table")

    status = workspace_subs.add_parser(
        "status",
        help=(
            "report dirty/clean, ahead/behind, merged? for owned worktrees "
            "(pays per-worktree git cost; optional slug or repo-set feature)"
        ),
    )
    status.add_argument(
        "slug",
        nargs="?",
        default=None,
        help=(
            "optional slug — owned worktree, or a repo-set feature "
            "(reports dirty/unpushed across every open member)"
        ),
    )
    status.add_argument("--json", action="store_true", help="emit JSON instead of text")

    clean = workspace_subs.add_parser(
        "clean",
        help="archive-not-delete owned scratch worktrees (bmad-loop clean discipline)",
    )
    clean.add_argument(
        "slug",
        nargs="?",
        default=None,
        help=(
            "optional slug — single owned worktree, or a repo-set feature "
            "(refuses while any member is dirty; names the dirty member)"
        ),
    )
    clean.add_argument(
        "--merged-only",
        action="store_true",
        help="only archive worktrees whose branch is already merged into its source",
    )
    clean.add_argument("--json", action="store_true", help="emit JSON instead of text")


def _add_upgrade_subparsers(upgrade_parser: argparse.ArgumentParser) -> None:
    """Add ``bmad-core`` (14.1–14.3), ``pin-fan-out`` (14.4), ``prove-landed`` (14.5)."""
    upgrade_subs = upgrade_parser.add_subparsers(
        dest="upgrade_verb", metavar="{bmad-core,pin-fan-out,prove-landed,verify}"
    )
    bmad_core = upgrade_subs.add_parser(
        "bmad-core",
        help=(
            "pre-flight (default) or deliberate --apply for a target bmad-method "
            "release; installer stays sole writer of _bmad/bmm/** and _bmad/core/**"
        ),
    )
    bmad_core.add_argument(
        "--target",
        required=True,
        metavar="X.Y.Z",
        help="target bmad-method release version (requires a packaged catalog entry)",
    )
    bmad_core.add_argument(
        "--apply",
        action="store_true",
        help=(
            "CAP-2 deliberate apply: require clean tree, consume CAP-1 pre-flight, "
            "create review branch, run `bmad-method install --action update -y`, "
            "verify _bmad/custom/** byte-identical (or report why not)"
        ),
    )
    bmad_core.add_argument(
        "--branch",
        default=None,
        metavar="NAME",
        help=(
            "review branch for --apply "
            "(default: steward/bmad-core-upgrade-<target>)"
        ),
    )
    bmad_core.add_argument(
        "--installer",
        default=None,
        metavar="BIN",
        help="override the bmad-method binary invoked by --apply (tests)",
    )
    bmad_core.add_argument(
        "--json",
        action="store_true",
        help="emit JSON instead of the human-readable report",
    )
    bmad_core.add_argument(
        "--package-root",
        default=None,
        metavar="DIR",
        help=(
            "optional path to an unpacked bmad-method package "
            "(reads removals.txt + upstream file copies; never installs from it)"
        ),
    )
    bmad_core.add_argument(
        "--catalog-dir",
        default=None,
        metavar="DIR",
        help="override the packaged release-catalog directory (tests)",
    )
    bmad_core.add_argument(
        "--repo-root",
        default=None,
        metavar="DIR",
        help="override the repo root used for installed-state reads (tests)",
    )
    bmad_core.add_argument(
        "--installed-version",
        default=None,
        metavar="X.Y.Z",
        help="override manifest installation.version (tests / retrodiction)",
    )

    pin_fan = upgrade_subs.add_parser(
        "pin-fan-out",
        help=(
            "CAP-4 report-only: enumerate known pin sites for a bmad-loop or "
            "bmad-method version change with moved/not-moved status; "
            "foreign-station sites are never edited"
        ),
    )
    pin_fan.add_argument(
        "--package",
        dest="pin_package",
        required=True,
        choices=("bmad-loop", "bmad-method"),
        help="which tool's pin fan-out to enumerate",
    )
    pin_fan.add_argument(
        "--from",
        dest="from_version",
        required=True,
        metavar="X.Y.Z",
        help="previous version (the floor still present on not-moved sites)",
    )
    pin_fan.add_argument(
        "--to",
        dest="to_version",
        required=True,
        metavar="X.Y.Z",
        help="target version (moved sites already reflect this floor)",
    )
    pin_fan.add_argument(
        "--repo-root",
        default=None,
        metavar="DIR",
        help="override the repo root used for pin-site reads (tests)",
    )
    pin_fan.add_argument(
        "--loops-home",
        default=None,
        metavar="DIR",
        help="override ~/.bmad-loops when reporting hook relays (tests)",
    )
    pin_fan.add_argument(
        "--json",
        action="store_true",
        help="emit JSON instead of the human-readable report",
    )

    prove = upgrade_subs.add_parser(
        "prove-landed",
        help=(
            "CAP-5 post-apply gate: bmad-drift integrity + CFE meta-tests + "
            "per-loop-home bmad-loop init (relay refresh) + validate; "
            "reports one pass/fail verdict"
        ),
    )
    prove.add_argument(
        "--repo-root",
        default=None,
        metavar="DIR",
        help="override the repo root used for drift + CFE gates (tests)",
    )
    prove.add_argument(
        "--loops-home",
        default=None,
        metavar="DIR",
        help="override ~/.bmad-loops when validating loop homes (tests)",
    )
    prove.add_argument(
        "--no-init",
        action="store_true",
        help=(
            "skip bmad-loop init relay refresh (validate-only); "
            "default runs init — the only documented foreign-tree mutation"
        ),
    )
    prove.add_argument(
        "--json",
        action="store_true",
        help="emit JSON instead of the human-readable report",
    )

    verify = upgrade_subs.add_parser(
        "verify",
        help=(
            "alias for prove-landed (CAP-5 post-apply single-verdict gate)"
        ),
    )
    verify.add_argument(
        "--repo-root",
        default=None,
        metavar="DIR",
        help="override the repo root used for drift + CFE gates (tests)",
    )
    verify.add_argument(
        "--loops-home",
        default=None,
        metavar="DIR",
        help="override ~/.bmad-loops when validating loop homes (tests)",
    )
    verify.add_argument(
        "--no-init",
        action="store_true",
        help=(
            "skip bmad-loop init relay refresh (validate-only); "
            "default runs init — the only documented foreign-tree mutation"
        ),
    )
    verify.add_argument(
        "--json",
        action="store_true",
        help="emit JSON instead of the human-readable report",
    )


def _add_suite_subparsers(suite_parser: argparse.ArgumentParser) -> None:
    """Add ``pipeline-truth`` (15.1) and ``advance`` (15.2). Story 15.3+ stay out."""
    suite_subs = suite_parser.add_subparsers(
        dest="suite_verb", metavar="{pipeline-truth,advance}"
    )
    truth = suite_subs.add_parser(
        "pipeline-truth",
        help=(
            "CAP-1: report upstream (npm/GitHub), recipe, channel, installed, "
            "and wired-or-not for all 13 bmad-suite packages — drift named "
            "per stage; every probe fail-open"
        ),
    )
    truth.add_argument(
        "--repo-root",
        default=None,
        metavar="DIR",
        help="override the repo root used for recipe/installed/wired probes (tests)",
    )
    truth.add_argument(
        "--baseline",
        action="store_true",
        help=(
            "without this flag the command live-probes the network; with it, "
            "replay the recorded 2026-08-22 research matrix offline (no network)"
        ),
    )
    truth.add_argument(
        "--json",
        action="store_true",
        help="emit JSON instead of the human-readable report",
    )
    advance = suite_subs.add_parser(
        "advance",
        help=(
            "CAP-2: advance one stale suite package end-to-end "
            "(autotick tag|head → build → test → publish → listing → "
            "reviewable PR; never auto-merged)"
        ),
    )
    advance.add_argument(
        "--package",
        required=True,
        metavar="NAME",
        help="suite package name (must be one of the 13 bmad-suite packages)",
    )
    advance.add_argument(
        "--repo-root",
        default=None,
        metavar="DIR",
        help="override the repo root used for truth/recipe resolution (tests)",
    )
    advance.add_argument(
        "--baseline",
        action="store_true",
        help=(
            "resolve staleness from the recorded 2026-08-22 research matrix "
            "instead of live probes (offline / fixtures)"
        ),
    )
    advance.add_argument(
        "--dry-run",
        action="store_true",
        help="plan and validate the chain without writing recipes, publishing, or opening a PR",
    )
    advance.add_argument(
        "--json",
        action="store_true",
        help="emit JSON instead of the human-readable advance report",
    )


def resolve_duty(name: str) -> Duty:
    """Return the duty implementation for *name*.

    `keys` returns a real `KeysDuty` (Story 1.3); `deploy` returns a real
    `DeployDuty` (Story 2.1); `provision` returns a real `ProvisionDuty`
    (Story 3.1); `budget` returns a real `BudgetDuty` (Story 4.1); `sync`
    returns a real `SyncDuty` (Story 8.1); `workspace` returns a real
    `WorkspaceDuty` (Story 13.1); `upgrade` returns a real `UpgradeDuty`
    (Stories 14.1–14.2); `suite` returns a real `SuiteDuty` (Story 15.1).
    No duty is `NullDuty` any more — the seam remains for a future ninth duty.
    """
    if name == "keys":
        # Imported here, not at module top: keys.py resolves its `_http.py`
        # bridge at import time and refuses to load outside a local-recipes
        # checkout, so a top-level import would take `steward --help`/
        # `--version` and every other duty down with it.
        from .keys import KeysDuty

        return KeysDuty()
    if name == "deploy":
        from .deploy import DeployDuty

        return DeployDuty()
    if name == "provision":
        from .provision import ProvisionDuty

        return ProvisionDuty()
    if name == "budget":
        from .budget import BudgetDuty

        return BudgetDuty()
    if name == "sync":
        # Imported here, not at module top, for the same reason as `keys`
        # above: sync.py imports keys.py directly (it reuses
        # HostScopedCredential/resolve_headers/repo_root verbatim), so it
        # inherits keys.py's own local-recipes-checkout guard.
        from .sync import SyncDuty

        return SyncDuty()
    if name == "workspace":
        from .workspace import WorkspaceDuty

        return WorkspaceDuty()
    if name == "upgrade":
        from .upgrade import UpgradeDuty

        return UpgradeDuty()
    if name == "suite":
        from .suite import SuiteDuty

        return SuiteDuty()
    return NullDuty(name)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        parser = build_parser()
        ns = parser.parse_args(argv)
        if not ns.duty:
            parser.print_help()
            return EXIT_OK
        result: DutyResult = resolve_duty(ns.duty).run(ns)
        print(result.summary, file=sys.stderr if not result.ok else sys.stdout)
        # A duty never calls sys.exit() (AD-8) — but it may name a specific
        # documented exit code (e.g. budget.EXIT_BUDGET_NOT_CONFIGURED) via
        # `DutyResult.details["exit_code"]` when the plain ok/not-ok binary
        # can't express it (budget check's three-way not-configured/under/
        # over signal, FR-18). main() is still the one that ACTS on it —
        # the decision stays sole-owned here, a duty only requests it.
        override = result.details.get("exit_code")
        if isinstance(override, int):
            return override
        return EXIT_OK if result.ok else EXIT_FAILED
    except KeyboardInterrupt:
        print("steward: interrupted", file=sys.stderr)
        return EXIT_INTERRUPTED
    except SystemExit as exc:
        # argparse raises this for --help/--version/usage. Legitimate codes pass
        # through; anything non-int is projected rather than trusted.
        code = exc.code
        if code is None:
            return EXIT_OK
        return code if isinstance(code, int) else EXIT_USAGE
    except Exception:                              # noqa: BLE001 — deliberate boundary
        import traceback
        traceback.print_exc()
        return EXIT_INTERNAL


if __name__ == "__main__":                          # pragma: no cover
    raise SystemExit(main())
