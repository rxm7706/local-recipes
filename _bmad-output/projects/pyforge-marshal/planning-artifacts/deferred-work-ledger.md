---
doc_type: deferred-work-ledger
project: pyforge-marshal
date: 2026-07-29
status: promoted-verbatim
---

# pyforge-marshal — deferred-work ledger (TRACKED)

**Promoted verbatim from Tier-3 on 2026-07-29 to make it durable.**

`implementation-artifacts/deferred-work.md` is **gitignored**: it does not survive a
clone or a bmad-loop worktree teardown, and this repo has already lost data that way
(pyforge-atlas's live ledger is still truncated to 11 of 64 entries, collateral of the
2026-07-19 copy failure). Until today this project had **no tracked ledger at all**, so
its entire deferred-work record — 4 KB — existed only in
scratch space. Found by `scripts/deferred_work_check.py`.

**This is a COPY, not a curation.** Bodies are unedited; nothing has been given a
resolution, re-severitied, or reconciled against what has since shipped. Treat entry
*status* fields as of their authoring date, not as current. The one intentional edit is
id renaming, below.

Durability first; curation is owned follow-up work.

## Ids renamed on promotion

- `DW-1` → **`DW-FU-1-1`** (story `1-1-package-spine-verdict-lattice-findings-registry…`) — bmad-loop emits a bare
  `DW-<n>` per run, which collides with the next damped story; renamed on promotion.

---

# Deferred Work

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
  summary: The `pyforge-mason`, `pyforge-steward`, and `pyforge-warden` `*-build-conda` pixi tasks (root `pixi.toml`) invoke `pixi build --manifest-path ...`, a flag the installed pixi (0.73.0) does not have (`pixi build --help` only exposes `--path`), so all three tasks fail when run.
  evidence: Confirmed live against the installed `pixi build --help` output while implementing Story 1.1's own `pyforge-marshal-build-conda` task, which mirrors the same block but was written with `--path` instead to avoid propagating the bug. Pre-existing in already-merged code; outside this story's declared surface (`src/shared/packages/pyforge-marshal/**` + root `pixi.toml` additions only).

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
  summary: `pyforge-doctor` and `pyforge-warden`'s package `.gitignore` files put comments inline after the `/dist/` and `/dist-conda/` patterns; gitignore has no trailing-comment syntax, so both patterns are dead and those directories are not ignored (steward/mason use bare lines and are fine; marshal's copy of the same defect was fixed in this story's review pass).
  evidence: Reproduced live during the Story 1.1 review — probe files created under `pyforge-marshal/dist/` appeared as untracked until the comments were moved to their own lines; doctor's and warden's `.gitignore` are byte-identical to the pre-fix marshal file. Pre-existing in already-merged sibling packages, outside this story's surface.

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
  summary: Every pyforge sibling package (doctor, warden, steward, mason, and now marshal) declares `license = { text = "MIT" }` in `pyproject.toml` but ships no LICENSE file in the package directory, so built wheels/sdists/conda artifacts carry no license text.
  evidence: `ls src/shared/packages/*/LICENSE*` returns nothing while every sibling `pyproject.toml` declares MIT. Repo-wide sibling convention predating this story; fixing marshal alone would diverge from the mirror-the-siblings mandate, so it needs a one-sweep fix across all five packages.

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
  summary: The `pyforge-mason-build-dist` and `pyforge-steward-build-dist` pixi tasks (root `pixi.toml`) run `python -m build` without `--no-isolation`, so `python -m build` creates an isolated venv and pip-fetches `hatchling` from PyPI — the `hatchling` deliberately provisioned in each feature block is dead weight, and the tasks hard-fail in the air-gapped/offline environments this repo explicitly supports (warden and doctor's equivalent tasks pass `--no-isolation`; marshal's copy of the same defect was fixed in this story's third review pass).
  evidence: Root `pixi.toml` shows warden/doctor build-dist cmds with `--no-isolation` and steward/mason without it; marshal's task mirrored steward/mason and was confirmed fixed live in this pass (wheel + sdist built successfully against the in-env hatchling with `--no-isolation` added). Pre-existing in already-merged sibling blocks, outside this story's surface.

### DW-FU-1-1: Follow-up review still recommended for 1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 1) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260725-234618-4c9d; this entry preserves the lingering recommendation for a deliberate later review.
status: open
