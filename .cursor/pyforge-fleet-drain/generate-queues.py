#!/usr/bin/env python3
"""Regenerate queues.yaml backlog from sprint-status-ledger.yaml files.

Usage:
  python3 .cursor/pyforge-fleet-drain/generate-queues.py
  python3 .cursor/pyforge-fleet-drain/generate-queues.py --summary

Preserves manual `order_overrides` and `skip_policies` in the existing queues.yaml
when present; otherwise uses ledger key sort order.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml or use pixi env")

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "queues.yaml"

STATIONS = (
    "atlas",
    "doctor",
    "herald",
    "marshal",
    "mason",
    "scribe",
    "steward",
    "warden",
)

STORY_KEY = re.compile(r"^\d+-\d+-")

# Explicit dispatch order where ledger sort is wrong (from epics / 2026-08-22 pause).
DEFAULT_ORDER_OVERRIDES: dict[str, list[str]] = {
    "marshal": [
        "11-5-referenced-dependency-verification-and-doctor-delegation",
        "11-6-marshal-seed-explain-and-version",
        "12-1-full-pixi-wiring-distribution-and-repo-gate-compliance",
        "12-2-the-local-recipes-empty-plan-oracle",
        "12-3-offline-operation-and-the-egress-counter",
        "12-4-pattern-meta-tests-and-the-never-write-proof",
        "12-5-cli-contract-idempotence-harness-and-performance-gates",
        "12-6-readme-adoption-guide-and-the-finding-remedy-reference",
        "15-1-one-command-refreshes-the-fleets-homes",
        "15-2-landing-promotes-the-ledger-and-staleness-is-its-own-check",
        "17-1-the-detectors-remaining-blind-spots-are-fixture-pinned-with-an-incident-log",
        "17-2-the-dreams-hygiene-mode-exists",
        "17-3-chain-completeness-audit-mode-reports-layers",
        "17-4-orchestrated-regeneration-that-cannot-lose-code-status",
        "18-1-marshals-capabilities-become-named-typed-tools",
        "18-2-parity-and-coverage-are-gated-numbers",
        "19-1-one-generator-produces-every-stations-test-architecture",
        "19-2-the-shared-test-support-kit",
        "19-3-coverage-gates-that-name-the-module",
        "19-4-test-architecture-stays-current-as-stories-land",
        "20-1-baseline-drift-detector-at-the-seam",
        "20-2-baseline-drift-defers-get-loud",
        "20-3-the-gated-upstream-filing",
        "20-4-intent-gap-attempts-are-preserved",
        "20-5-missing-preserve-detector",
        "20-6-the-verify-scope-primitive",
        "20-7-both-guards-hard-fail-on-drift",
        "20-8-the-landing-evidence-grammar",
        "20-9-doctor-consumes-the-grammar",
        "20-10-marshal-consumes-the-grammar",
        "21-1-chain-completeness-audit-mode-extends-layer-presence-into-full-cap-3-coverage",
        "21-2-orchestrated-chain-regeneration",
        "21-3-code-status-preservation",
        "21-4-orphan-detection-with-review-gated-cleanup",
        "21-5-configurable-per-project-invocation",
        "22-1-the-dispatch-verb-launches-one-governed-isolated-story-session",
        "22-2-completion-is-judged-from-git-and-process-facts-and-a-zombie-is-never-redispatched",
        "22-3-verification-is-the-product-no-landing-on-a-self-report",
        "22-4-a-verified-story-lands-through-the-existing-machinery-classified-marshal-native",
        "22-5-one-story-in-flight-per-station-stations-in-parallel-overlap-is-loud",
        "22-6-the-dispatched-run-survives-its-operator-and-its-journal-carries-the-timing-signal",
        "23-1-wall-clock-fallback-derivation-from-promoted-spec-revision-fields",
        "23-2-wall-clock-is-never-blended-with-active-compute",
        "23-3-the-coverage-caption-partitions-by-true-reason",
        "24-1-marshal-gains-the-missing-liveness-primitive",
        "24-2-the-operator-answer-is-one-documented-command",
        "24-3-an-unsupervised-row-has-a-cheap-documented-double-check",
        "25-6-a-hand-driven-runs-deferrals-reach-the-ledger-unaided",
        "25-7-the-factorys-living-docs-are-re-grounded-with-a-named-owner",
    ],
    "steward": [
        "12-3-air-gap-parity-is-a-failing-check",
        "12-4-the-cluster-bring-up-is-documented-reproducible-and-key-disciplined",
        "12-5-the-db-gpt-sidecar-joins-the-chart",
        "12-6-redis-is-hardened-still-ephemeral",
        "12-7-the-12-1-tier-3-items-are-verified-on-the-live-cluster",
        "12-8-github-projects-v2-lands-in-github-metrics-via-dlt",
        "12-9-ocp-as-a-portability-profile",
        "13-1-workspace-verbs-over-git-worktree",
        "13-2-status-and-the-feed-mirror-decision",
        "13-3-a-repo-set-opens-as-one-workspace",
        "13-4-the-set-reports-and-tears-down-safely",
        "14-1-the-pre-flight-diff-retrodicts-a-real-upgrade",
        "14-2-apply-is-deliberate-branched-and-never-clobbers-custom",
        "14-3-clobbered-custom-surfaces-are-caught-and-re-applied",
        "14-4-the-pin-fan-out-is-enumerated-not-discovered-by-red-tests",
        "14-5-one-command-proves-the-upgrade-landed",
        "15-1-one-command-reports-the-whole-pipelines-truth",
        "15-2-one-command-advances-a-stale-package-end-to-end",
        "15-3-five-modules-wire-through-the-provisioning-verb",
        "15-4-the-upgrade-gate-spot-checks-one-native-path-per-class",
        "16-1-dependencies-are-pixi-sourced-single-authority",
        "16-2-startup-refuses-misconfiguration-two-stage-and-named",
        "16-3-every-process-speaks-structlog-otel",
        "16-4-policy-is-a-test-suite",
        "16-5-identity-is-oidc-delegated-no-local-passwords",
        "17-1-steward-init-shell-init-detect-and-prepare-the-machine",
        "17-2-steward-setup-initrepo-take-the-machine-to-green",
    ],
}


def ledger_path(station: str) -> Path:
    return (
        REPO
        / "_bmad-output"
        / "projects"
        / f"pyforge-{station}"
        / "planning-artifacts"
        / "sprint-status-ledger.yaml"
    )


def backlog_from_ledger(station: str) -> list[str]:
    path = ledger_path(station)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    dev = data.get("development_status") or {}
    return sorted(k for k, v in dev.items() if STORY_KEY.match(k) and v != "done")


def apply_order(backlog: list[str], override: list[str] | None) -> list[str]:
    if not override:
        return sorted(backlog)
    ordered = [k for k in override if k in backlog]
    tail = sorted(k for k in backlog if k not in ordered)
    return ordered + tail


def load_existing() -> dict:
    if not OUT.exists():
        return {}
    return yaml.safe_load(OUT.read_text()) or {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    existing = load_existing()
    overrides = existing.get("order_overrides") or DEFAULT_ORDER_OVERRIDES
    skip_policies = existing.get("skip_policies") or [
        {
            "station": "steward",
            "story": "12-7-the-12-1-tier-3-items-are-verified-on-the-live-cluster",
            "action": "skip_on_blocked",
            "reason": "Requires live OCP cluster; dispatch 12-8 next and report skip to operator.",
        }
    ]
    campaign = existing.get("campaign") or {
        "mode": "drain_to_zero",
        "updated": "2026-08-23",
        "coordinator": "cursor-hand-driven",
    }

    stations: dict = {}
    total_remaining = 0
    for s in STATIONS:
        backlog = backlog_from_ledger(s)
        queue = apply_order(backlog, overrides.get(s))
        drained = len(backlog) == 0
        stations[s] = {
            "project": f"pyforge-{s}",
            "drained": drained,
            "remaining_count": len(queue),
            "next": queue[0] if queue else None,
            "queue": queue,
        }
        total_remaining += len(queue)

    doc = {
        "campaign": campaign,
        "skip_policies": skip_policies,
        "order_overrides": overrides,
        "stations": stations,
    }

    if args.summary:
        print(f"Total backlog stories: {total_remaining}")
        for s in STATIONS:
            st = stations[s]
            mark = "DRAINED" if st["drained"] else f"{st['remaining_count']} left"
            nxt = st["next"] or "—"
            print(f"  {s:8} {mark:12} next={nxt}")
        return 0

    header = """# GENERATED — run: python3 .cursor/pyforge-fleet-drain/generate-queues.py
# Hand-edit order_overrides / skip_policies / campaign.mode only; re-run to refresh backlog from ledgers.

"""
    OUT.write_text(header + yaml.dump(doc, sort_keys=False, allow_unicode=True))
    print(f"Wrote {OUT} ({total_remaining} backlog stories)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
