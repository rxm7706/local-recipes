# Finding → remedy reference

Every conformance problem `marshal seed check` (and the mutating verbs' preflight) can report uses a closed `FindingType` vocabulary. Each type has a fixed severity and remedy — the same strings as `seed/detect/findings.py::REMEDIES` (NFR-M3). Use this table when CI or a local check prints a finding you do not recognize.

Severity ladder (AD-54, borrowed from `bmad_drift_check.py`):

| Severity | Meaning for `check` |
|---|---|
| **HARD** | Breaks the conformance contract; `marshal seed check` exits **1**. With `--strict`, **DRIFT** also fails. |
| **DRIFT** | Stale or incomplete, but not corrupt; exits **0** unless `--strict`. |
| **INFO** | Advisory only; never fails the run. |

## Finding → remedy mapping

| Finding | Severity | Remedy |
|---|---|---|
| `artifact-missing` | HARD | Run `marshal seed adopt` (or `init`, for a first-ever install) to materialize it. |
| `managed-file-modified` | HARD | The file is tool-owned -- revert the local edit, or run `marshal seed update --force` to accept it as the new baseline. |
| `managed-region-modified` | HARD | Revert edits inside the managed region, or run `marshal seed update --force` to overwrite it; content outside the markers is untouched. |
| `managed-region-missing` | DRIFT | Run `marshal seed update` to re-insert the region at its declared anchor. |
| `derived-stale` | DRIFT | Run `marshal seed update` to recompute it; this class is always safe to regenerate. |
| `model-behind` | DRIFT | Run `marshal seed update` to upgrade the repo to the currently installed model version. |
| `state-invalid` | HARD | Restore `.marshal/seed-state.yml` from version control, or run `marshal seed adopt` to rebuild it; never hand-edit state. |
| `never-write-violation` | HARD | No repo action needed -- this names a bug in the plan builder or manifest; file an issue against Genesis. |
| `referenced-dep-missing` | DRIFT | Install the missing dependency at or above its declared floor (`marshal doctor check` can do this where available). |
| `uncovered` | HARD | Fix the manifest entry -- give it a valid `class`, or `unclassified-deferred` with a `rationale`. |
| `legacy-present` | INFO | Informational only, no action required; migrate to the named successor by hand when ready. |
| `opted-out` | INFO | Informational -- while this opt-out stands the tool will not re-insert this region. To bring it back under management, run `marshal seed adopt --reinstate <artifact>#<region>`. |
| `kit-item-missing` | DRIFT | Run `marshal seed kit --apply` in the loop home to provision it, or turn its `[context]` layer off if this home does not want it. |
| `kit-item-stale` | DRIFT | Run `marshal seed kit --apply` to refresh it; the item is there but no longer matches what produced it. |
| `kit-instrument-unavailable` | INFO | Advisory -- install the named instrument (or accept the platform gap); the layer stays off and nothing is blocked. |

## Related commands

```bash
marshal seed check --repo-root .              # human-readable report
marshal seed check --repo-root . --strict     # fail on HARD and DRIFT
marshal seed check --repo-root . --json        # CI-annotatable JSON
```

When `doctor` is on `PATH`, referenced-dependency findings may be prefixed with `[doctor]` — the type and remedy are unchanged.
