---
sources:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/accept.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/kit.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/manifest.yaml
  - src/shared/packages/pyforge-marshal/tests/meta/test_seed_accept_remedy_surfaces.py
verified: 2026-11-17
---

# How to adopt the operating model in another repository with `marshal seed`

Use the `marshal seed` verbs to deliver this repository's operating model into another git repo. Genesis (the seed installer inside `pyforge-marshal`) only shapes structure and conventions; Marshal operates the machinery after install. This guide walks the **brownfield** path: a repo that already has content and history.

## When to use this

- You are layering the operating model onto an existing repository.
- You are upgrading an adopted repository to a newer model version.
- You edited a tool-owned file on purpose and need the guard to accept it.
- You are provisioning a loop home's token-economy kit by hand.
- You are wiring the conformance check into CI.

> [!NOTE]
> **Prerequisites.** A **git** repository (non-git targets forfeit the update story). **pixi** (or another conda environment) with `pyforge-marshal` installed: in this repository, `pixi run -e pyforge-guild marshal …`. Optional: `doctor` on `PATH` for richer referenced-dependency checks.

## Two version numbers

Genesis tracks two independent clocks (architecture A-05):

| Field | Where | Meaning |
|---|---|---|
| **`model_version`** | Bundled `templates/manifest.yaml` + recorded in `.marshal/seed-state.yml` | The operating model's semver — manifest entries' `since`/`until` bounds are keyed against this. |
| **`seed_model_version`** | `.marshal/seed-state.yml` only | The Genesis package release that last wrote state (this repo's `pyforge-marshal` version). |

`marshal seed check` compares them and emits `model-behind` when the repo's recorded `model_version` is older than the installed manifest.

## State file

Genesis writes **one** tool-owned state file at `.marshal/seed-state.yml` (FR-102). It records what was installed, managed hashes, opt-outs, skips, and legacy paths — never hand-edit it. Copier's `.copier-answers.yml` is opaque to Genesis; answers are re-supplied programmatically on every engine call (AD-52).

Inspect versions without mutating:

```bash
marshal seed version --repo-root .
marshal seed explain <artifact-id>
```

## Steps

### 1. Dry-run and review the plan

Default for `adopt` is dry-run (no writes):

```bash
marshal seed adopt --repo-root . --agents claude,cursor
```

Review the printed plan: which artifacts will be materialized, which managed regions will be inserted, and which paths are skipped. Resolve blockers (never-write collisions, missing referenced deps) before applying.

For a **greenfield** directory instead of brownfield:

```bash
marshal seed init /path/to/new-repo --slug my-project --agents claude,cursor
```

`init` applies directly by default; pass `--dry-run` to compute the plan without applying it.

### 2. Apply

When the plan looks correct:

```bash
marshal seed adopt --repo-root . --agents claude,cursor --apply --yes
```

Use `--skip <glob>` to exclude specific manifest paths. The pattern is recorded in state and honoured on every later `adopt` and `update` run as well (FR-87), so a skipped artifact stays skipped without repeating the flag. Bringing a previously opted-out managed region back under management has no flag yet; see [Marshal seed managed regions](../reference/marshal-seed-managed-regions.md).

### 3. Upgrade later

When a newer Genesis release ships a higher `model_version`:

```bash
marshal seed update --repo-root .                # dry-run plan
marshal seed update --repo-root . --run --yes    # apply it
```

Review the two-phase plan (migrations, then materialization). Use `--force` only when you intend to **discard** local edits to tool-owned files: it skips the hand-edit refusal and regenerates from the packaged template (FR-101). It does not record an edit as the new baseline; `marshal seed accept` does (next step).

### 4. Record an intended edit

When you meant to edit a tool-owned file (a `copied-managed` file, or a region inside a `hybrid-managed-region` file), `adopt` and `update` refuse with `managed-content-modified` and `check` reports `managed-file-modified` or `managed-region-modified`. Commit the edit, then record it as the new baseline with `marshal seed accept`, the eighth verb:

```bash
marshal seed accept bmad-switch                                          # dry run: prints <recorded> -> <current>
marshal seed accept bmad-switch --apply --reason "carry the fix for X"   # re-record it
marshal seed accept gitignore#model-ignores --apply --reason "..."       # one region of a hybrid file
marshal seed accept gitignore --apply --reason "..."                     # every region state records
```

`accept` is a dry run by default and writes nothing then, `.marshal/plan.json` included. With `--apply` it needs `--reason` and a clean worktree (so the accepted bytes are committed bytes and git stays the undo). It writes one file, `.marshal/seed-state.yml`, in one atomic replace: the new hash, and one entry in the optional `acceptances` journal (id, region, path, previous and accepted hash, time, who, the commit it ran at, and your reason). A hash that has not changed writes nothing and exits 0.

It refuses (exit 3) an artifact state does not record, a class no guard reads (`copied-seeded`, `generated-derived`, `referenced`, `unclassified-deferred`, or a directory entry), a skipped or absent path, a hybrid file whose regions do not parse, and a git identity git cannot resolve. An id the manifest does not declare is a usage error (exit 2). `accept` records what is on disk; it does not judge whether the edit was right. The guard still catches an edit nobody accepted, and the journal says who accepted what and why.

### 5. Provision a loop home's token-economy kit

`marshal seed kit` is the seventh verb and the only one scoped to a **loop home** rather than a repo. It provisions the per-home token-economy kit (Story 28.3): the caveman output-compression skill with Genesis's articulate carve-out, the loop-home-scoped CCR store directory, and the codegraph structure index. Each item is gated by its own `[context]` layer in the composed policy, so a home that declares no `[context]` block gets nothing and reports nothing.

```bash
marshal seed kit --repo-root <loop-home>            # dry-run (default)
marshal seed kit --repo-root <loop-home> --apply    # provision
```

`marshal preflight` runs the same provisioning automatically for the home it is checking, so this verb is for provisioning a home by hand or for inspecting what preflight would do.

Three things worth knowing before enabling a layer:

- **It never blocks.** No kit finding is HARD, and `marshal seed kit` exits `0` on every completed run. An instrument that is not installed (caveman and codegraph are linux-64 only) skips its layer with a named `kit-instrument-unavailable` finding at **INFO** — advisory even under `--strict`.
- **A first index build is slow.** With the `structure-graph` layer enabled and no index yet, this runs a real `codegraph init` unattended; the ceiling is 900s (an incremental resync, 300s). A timeout degrades into a named finding, never a hang.
- **`marshal seed check` verifies it.** The kit's three checks appear in the report (text and `--json`) whenever the target's `[context]` resolves, including the passing and declared-off ones.

Which project's policy supplies the `[context]` declaration is resolved from `--project`, then `BMAD_ACTIVE_PROJECT`, then the home's own `_bmad/custom/.active-project` marker — so inside a provisioned home no flag is needed.

### 6. Wire `check` into CI

Add a job that fails on conformance drift:

```yaml
# Example GitHub Actions step (adjust pixi/env to your setup)
- name: Genesis conformance
  run: |
    pixi run -e pyforge-marshal marshal seed check --repo-root . --strict
```

Use `--json` if your CI annotates findings on pull requests. Without `--strict`, only **HARD** findings fail the command; with `--strict`, **DRIFT** fails too (recommended for main-branch protection). Every finding and its remedy is listed in [Marshal seed findings and their remedies](../reference/marshal-seed-findings.md).

## What you get

An adopted repository carries the model's files, a `.marshal/seed-state.yml` recording what was installed, and a `check` that reports drift from it.

Every manifest entry is one of five product classes (plus `unclassified-deferred`, a maintainer-only escape hatch). The guard follows the manifest's **current** class, not the class a state record stored when the file was claimed:

| Class | On `update` | On hand-edit |
|---|---|---|
| **referenced** | Nothing in the repo changes (verify presence + floor only) | n/a |
| **copied-managed** | Regenerated wholesale | `check` reports; `update` refuses unless you `marshal seed accept` the edit (record it) or pass `--force` (discard it) |
| **copied-seeded** | Never touched after first install | Expected and fine — repo-owned forever |
| **generated-derived** | Recomputed every run (idempotent) | Overwritten on next run; `check` may report `derived-stale` |
| **hybrid-managed-region** | Only the marker-delimited span is replaced | `check` reports hash mismatch on the span only |

Marker semantics and the opt-out are in [Marshal seed managed regions](../reference/marshal-seed-managed-regions.md). The full V1 inventory rationale is `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/extraction-manifest.md`.

## Air-gapped sites

Templates ship inside the conda package and the Copier engine is conda-provisioned, so the seed verbs make no runtime network fetch. See [How to use Marshal's seed and substrate bootstrap in an air-gapped site](use-marshal-in-an-air-gapped-site.md).
