---
sources:
  - scripts/detectors.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
  - docs/reference/judgement-vocabulary.md
  - docs/dreams/fidelity-enforcement.md
verified: 2026-09-20
---

# The Detector Framework

PyForge maintains continuous estate governance via its **Detector Framework**. Detectors are standalone, offline, deterministic checks that enforce invariants on both the codebase and the operator's runtime environment.

This document explains the architectural rationale behind the framework. For instructions on running them, see [How to run and understand Detectors](../how-to/run-and-understand-detectors.md).

## Dynamic Registry Discovery

Unlike many systems that maintain a hand-authored list of checks, PyForge's `scripts/detectors.py` registry is derived from the filesystem.

*Why?* A hand-written list almost always omits exactly the newest addition. On 2026-07-31 this repo had three registries of its own detectors and no two agreed. So the registry scans `scripts/*_check.py` and `docs/dashboard/check_*.py`, reads each file's `DETECTOR = {"scope": ...}` declaration with `ast` (never by importing — a detector's module body may open files or shell out), and fails on its own gaps.

If a script looks like a detector but declares no `DETECTOR` scope, or declares one but has no matching pixi task, the framework surfaces that as a *registry finding*. The registry cannot silently omit a detector, which is the only property that makes it worth having.

One deliberate exception: the detectors that were ported into `pyforge.doctor.sources` (Story 6.9 and later) have no script file left to scan. `detectors.py` threads them in from `pyforge.doctor.sources.REGISTRY` in-process, into the same results list and the same exit-code aggregation; if `pyforge.doctor` cannot be imported they degrade to *unknown* rows rather than vanishing.

## Scope: Repo vs. Runtime

The framework explicitly splits detectors into two domains:

1. **`scope="repo"`**: These read tracked files only. They can run anywhere, including CI runners (`detectors-ci`).
2. **`scope="runtime"`**: These read host state, such as the gitignored Tier-3 sprint feeds, tmux panes, and `~/.bmad-loops`. They explicitly *cannot* run in CI.

This split is intentional. It represents the factory's missing observation plane showing up as a deployment constraint: runtime detectors are precisely the ones with nowhere to run in an ephemeral CI runner, which is why they are executed by operators and agent watchdogs locally (`docs/dreams/fidelity-enforcement.md` is the Dream that closes that gap).

## "Unknown, Never Green"

PyForge's detector registry exit codes obey a strict rule regarding failure to run.

* Exit `0` means every selected detector ran and passed.
* Exit `1` means at least one detector ran and reported findings.
* Exit `2` means at least one detector **could not run**, and none reported findings.

Exit code 2 is not a softer 0. If a detector crashes, times out, or fails to import a dependency, it reports `unknown`. The framework never treats a failure to measure as a clean bill of health. This ensures the dashboard status strip (and CI gates) never claim "green" for an invariant they didn't actually verify.

Note that a *single* Doctor source run on its own (`python -m pyforge.doctor.sources <name>`, which is what the per-detector pixi tasks call) projects through a different exit-code domain — `pyforge.doctor.verdict.exit_code_for`, where any `fail` finding exits `2` and `warn` never changes the exit code. The two domains and the `2`-inversion trap are tabled in [`judgement-vocabulary.md`](../reference/judgement-vocabulary.md) § *Severity and exit codes*.
