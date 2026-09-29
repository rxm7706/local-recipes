---
sources:
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - scripts/spec_surface_check.py
  - scripts/.spec-surface-baseline.json
  - _bmad/scripts/memlog.py
  - .claude/memory/feedback/spec-surface-check-py-s-write-baseline-reads-git-ls-files-so.md
verified: 2026-09-20
---

# How to Reconcile Spec Surface Drift

PyForge governs every tracked file under a Spec's *surface* (its manifest of files) or an explicit allowlist (`scripts/spec_surface_allowlist.txt`). The `spec-surface-check` detector enforces this by verifying that every change to a governed file is accompanied by movement in the owning Spec's `.memlog.md`, against the hashes stamped in `scripts/.spec-surface-baseline.json`.

If you add, modify, or remove a governed file without the memlog moving, the CI `detectors-ci` lane fails with a `drift` finding. If the memlog moved but does not name the changed path, you get a `drift-presumed` warning instead.

This guide explains how to safely reconcile that drift.

## Step 1: Identify the Governing Spec

When `spec-surface-check` fails, it prints exactly which spec governs the file and what to do:

```
[spec-surface] drift: fail -- pyforge-doctor/spec-pyforge-doctor: docs/MAP.md changed but the spec's memlog did not move — reconcile the spec, then --write-baseline --spec pyforge-doctor/spec-pyforge-doctor
```
In this example, the governing spec is `spec-pyforge-doctor`, owned by the `pyforge-doctor` station; the spec key is `pyforge-doctor/spec-pyforge-doctor`.

## Step 2: Append a Memlog Event

You must explicitly document *why* the file changed by appending an event to the Spec's `.memlog.md`. Use the append-only `memlog.py` utility rather than editing the file by hand (it is atomic and never rewrites history; the one exception is a memlog with no frontmatter, which `memlog.py` refuses — append that one by hand in the same one-line shape).

```bash
python _bmad/scripts/memlog.py append \
  --workspace _bmad-output/projects/<station>/planning-artifacts/specs/<spec> \
  --type event \
  --text "Surface reconcile <date>: updated <file> to clarify X"
```

*Example:*
```bash
python _bmad/scripts/memlog.py append \
  --workspace _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor \
  --type event \
  --text "Surface reconcile 2026-09-19: updated docs/MAP.md with new detector how-tos"
```

Name every changed path in the text — a memlog that moved without naming the path only downgrades the finding to `drift-presumed`.

## Step 3: Stage New Files

The baseline stamper takes its *file list* from `git ls-files`, so a brand-new file must be staged before stamping or it is silently left out of the baseline. The *hashes* it stamps come from the working tree, so stamp only when the tree holds exactly the state you mean to bless.

```bash
git add <the files you added>
```

Stage the specific paths you changed rather than `git add .` — check first whether another session is working in the same checkout ([Detecting concurrent agent activity](detect-concurrent-agent-activity.md)).

## Step 4: Stamp the Baseline

Once the files are staged and the memlog is updated, stamp the new spec surface baseline. **You must scope the stamp to the specific spec that drifted.**

```bash
python scripts/spec_surface_check.py --write-baseline --spec <station>/<spec>
```

*Example:*
```bash
python scripts/spec_surface_check.py --write-baseline --spec pyforge-doctor/spec-pyforge-doctor
```

`--spec` is repeatable when several specs drifted. Run it with plain `python` from the `pyforge-guild` env — the script is a mutation-only residual; the read-only verdict lives in `pyforge.doctor.sources`.

> [!CAUTION]
> **Never run a bare `--write-baseline` without `--spec`.** A bare stamp covers every spec in the repository, accepting all pending drift — including undocumented changes your colleagues are working on in parallel worktrees — as correct.

A stamp is only valid until the next edit of any file in that spec's surface. If you touch a governed file again after stamping, repeat Steps 2–4.

## Step 5: Verify

Re-run the detector to ensure the drift is cleared:
```bash
pixi run -e pyforge-guild spec-surface-check
```
Read its exit code directly, never through a pipe: `0` is clean, `2` means a `fail` finding remains (this single-source run uses Doctor's own exit domain, not the `detectors` aggregator's — see [`judgement-vocabulary.md`](../reference/judgement-vocabulary.md) § *Severity and exit codes*). Commit the memlog, the baseline, and your change together.
