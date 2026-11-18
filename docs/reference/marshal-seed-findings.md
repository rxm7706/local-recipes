---
sources:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/findings.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_finding_remedy_reference_sync.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_findings.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/referenced_deps.py
verified: 2026-11-18
---

# Marshal seed findings and their remedies

Every conformance problem `marshal seed check` (and the mutating verbs' preflight) can report uses a closed `FindingType` vocabulary. Each type has a fixed severity and remedy — the same strings as `REMEDIES` in `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/findings.py` (NFR-M3). Use this table when CI or a local check prints a finding you do not recognize.

The table is held to the code: marshal's `test_finding_remedy_reference_sync.py` reds when a `FindingType` is missing here or a remedy string differs from `REMEDIES`. Change the remedy in `findings.py` first, then copy it here. Every `marshal …` command a remedy names is also held to the CLI: marshal's `test_seed_detect_findings.py` walks each one through the real argument parser and reds on a verb or flag that does not exist.

Severity ladder (AD-54, borrowed from `bmad_drift_check.py`):

| Severity | Meaning for `check` |
|---|---|
| **HARD** | Breaks the conformance contract; `marshal seed check` exits **1**. With `--strict`, **DRIFT** also fails. |
| **DRIFT** | Stale or incomplete, but not corrupt; exits **0** unless `--strict`. |
| **INFO** | Advisory only; never fails the run. |

## Finding → remedy mapping

| Finding | Severity | Remedy |
|---|---|---|
| `artifact-missing` | HARD | Run `marshal seed adopt --apply` (or `init`, for a first-ever install) to materialize it. |
| `managed-file-modified` | HARD | The file is tool-owned -- revert the local edit, run `marshal seed accept <artifact-id> --apply --reason "..."` to record an intended edit as the new baseline, or run `marshal seed update --run --force` to discard the edit. |
| `managed-region-modified` | HARD | Revert edits inside the managed region, run `marshal seed accept <artifact-id>#<region> --apply --reason "..."` to record an intended edit as the new baseline, or run `marshal seed update --run --force` to discard the edit and overwrite the region; content outside the markers is untouched. |
| `managed-region-missing` | DRIFT | Run `marshal seed update --run` to re-insert the region at its declared anchor. |
| `derived-stale` | DRIFT | Run `marshal seed update --run` to recompute it; this class is always safe to regenerate. |
| `model-behind` | DRIFT | Run `marshal seed update --run` to upgrade the repo to the currently installed model version. |
| `state-invalid` | HARD | Restore `.marshal/seed-state.yml` from version control, or run `marshal seed adopt --apply` to rebuild it; never hand-edit state. |
| `never-write-violation` | HARD | No repo action needed -- this names a bug in the plan builder or manifest; file an issue against Genesis. |
| `referenced-dep-missing` | DRIFT | Install the missing dependency at or above its declared floor, then run `marshal seed check` again to confirm it; Genesis verifies referenced dependencies and never installs them. |
| `uncovered` | HARD | Fix the manifest entry -- give it a valid `class`, or `unclassified-deferred` with a `rationale`. |
| `legacy-present` | INFO | Informational only, no action required; migrate to the named successor by hand when ready. |
| `opted-out` | INFO | Informational -- while this opt-out stands the tool will not re-insert this region. To bring it back under management, restore the region's begin and end markers by hand, then run `marshal seed update --run` to record it. |
| `kit-item-missing` | DRIFT | Run `marshal seed kit --apply` in the loop home to provision it, or turn its `[context]` layer off if this home does not want it. |
| `kit-item-stale` | DRIFT | Run `marshal seed kit --apply` to refresh it; the item is there but no longer matches what produced it. |
| `kit-instrument-unavailable` | INFO | Advisory -- install the named instrument (or accept the platform gap); the layer stays off and nothing is blocked. |
| `target-escapes-repo` | HARD | Fix the manifest entry's path, or the in-repo symlink it resolves through, so it stays inside the repository; every other artifact is applied regardless. |
| `slug-unresolved` | INFO | Pass `--project <slug>` (or set `BMAD_ACTIVE_PROJECT`, or the target's `_bmad/custom/.active-project` marker) so the entry is checked at the path it renders to. |
| `artifact-skipped` | INFO | The artifact is absent but matches a skip recorded in `.marshal/seed-state.yml` -- remove the skip from state if it should be materialized, or run `marshal seed adopt` with `--skip` unchanged to leave it alone. |

## Commands that print findings

```bash
marshal seed check --repo-root .              # human-readable report
marshal seed check --repo-root . --strict     # fail on HARD and DRIFT
marshal seed check --repo-root . --json        # CI-annotatable JSON
```

Referenced-dependency findings come from marshal's own local probe. With `doctor` on `PATH`, `check` first asks Doctor for a `genesis-referenced-deps` source and prefixes what it returns with `[doctor]`; Doctor ships no such source (checked 2026-11-18: the call exits 2), so the local probe answers. The type and remedy are the same either way.
