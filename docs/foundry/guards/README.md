# Guard library (hub:CAP-4)

Steward owns the catalog. A Spec names what it lacks with a `hub_guards:`
list, then `steward guards lacking --spec PATH`.

Warden stays the sole PR verdict. Doctor stays advisory. These verbs are
**not** members of `detectors` / `detectors-ci`.

| Category | In library | Surfaces |
|---|---|---|
| algorithmic | yes | `*-check` detectors, Warden lattice |
| consensus | yes | parallel review lenses |
| expert | yes | `gate_mode`, AGENTS operator-confirmation |
| policy_and_safety | yes | Warden license/vuln/waiver, marshal MRS-GATEs |
| regression_and_drift | yes | bmad-drift-check, spec-surface, doctor frozen_path |
| source_grounding | yes (first addition) | scribe recall AD-8; `steward guards source-ground` on dev/review text |
| outcome | **no** | blocked on `docs/dreams/build-league-scorecard.md` |

```bash
pixi run -e pyforge-steward steward guards catalog
pixi run -e pyforge-steward steward guards lacking
pixi run -e pyforge-steward steward guards lacking --spec path/to/SPEC.md
pixi run -e pyforge-steward steward guards source-ground --text notes.md --repo .
```
