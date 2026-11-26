---
sources:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - .claude/memory/feedback/upgrade-bmad-core-and-the-skf-custom-module-only-through-pix.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/failure-modes.md
verified: 2026-11-26
---

# How to upgrade BMAD core

Use the `pyforge steward upgrade` duty to move this repository's installed BMAD-METHOD core to a new release without losing the repository's own edits to installer-owned files.

## When to use this

- A new `bmad-method` release is out and you want to know what it would change here.
- You are ready to apply a release on a review branch.
- A pin moved and you want to see every place that still names the old version.
- An upgrade was applied and you need one verdict that it landed cleanly.

## When to skip this

- You want to refresh ordinary dependency pins. See [How to refresh the estate](refresh-the-estate.md).
- You only want to know which BMAD version and modules are installed. Read the generated `docs/reference/bmad-estate-llms-full.md`.

:::caution
Never upgrade with a raw `bmad-method install` or `bmad-module-skill-forge update`. A raw update of the skf module once dropped local edits to installer-owned files; the steward apply re-applies them. Never run `bmad-module-skill-forge uninstall`: its manifest lists every file under the skills directory.
:::

:::note
**Prerequisites.** Run from the repository root. The target release needs a curated catalog file, `<version>.yaml`, under `src/shared/packages/pyforge-steward/src/pyforge/steward/data/bmad_core_releases/`. Without one the duty cannot report on that target; adding the catalog is its own story.
:::

## Steps

### 1. Read the pre-flight report

```bash
pixi run -e pyforge-guild pyforge steward upgrade bmad-core --target <X.Y.Z>
```

Without `--apply` this is report-only and writes nothing. It prints the installed and target versions, the numbered traps the target trips, and one section per risk:

```text
steward upgrade bmad-core — pre-flight (report-only)
installed: 6.12.2
target:    6.12.2
traps:     1, 4, 9, 11

## Skill changes (adds / removes / renames)
## removals.txt deletions [trap 3]
## Upstream-touched files with local modifications
## Legacy _bmad/custom/** overrides that halt shims
## New hard prerequisites
## Forwarder / orchestrator contract changes
## Config-format migration
## Custom modules (catalog vs installed manifest)
## Local customizations (installer-owned files edited in place)
## Shims to retire (--no-shims candidates) [0]
## Notes
```

Each trap number is an entry in `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/failure-modes.md`. Read every section that is not `(none)` before you go on. Add `--json` for a machine-readable report.

To have the report compare installer-owned files against the cached installed package, pass `--installed-package-root DIR`; to read the target's own `removals.txt` and file copies, pass `--package-root DIR`.

### 2. See where the pin fans out

```bash
pixi run -e pyforge-guild pyforge steward upgrade pin-fan-out --package bmad-method --from <X.Y.Z> --to <X.Y.Z>
```

This is report-only too. It lists every known pin site as `moved` or `not_moved`. `--package` is `bmad-method` or `bmad-loop`. A site marked `foreign` belongs to another station: steward reports it and never edits it, so its owner moves it.

### 3. Apply on a review branch

```bash
pixi run -e pyforge-guild pyforge steward upgrade bmad-core --target <X.Y.Z> --apply \
  --package-root .pixi/envs/pyforge-guild/lib/node_modules/bmad-method
```

`--apply` requires a clean tree. It reads the pre-flight, creates a review branch (`steward/bmad-core-upgrade-<target>`, or `--branch NAME`), runs the BMAD installer with the repository and every installed module named explicitly, restores each custom module's configuration and runs that module's own installer, and checks that `_bmad/custom/**` is byte-identical afterwards.

Pass `--package-root`. Without it the apply still finds and reports local customizations but does not re-apply them.

The apply leaves the checkout on the review branch with the changes uncommitted. Review the diff, commit, and land it through a pull request like any other change. An installer run that exits `0` but changes nothing is reported as a refusal, not a success.

`--no-shims` also retires the installed core's deprecation shims; it is refused while a legacy-name override exists under `_bmad/custom/`.

### 4. Prove it landed

```bash
pixi run -e pyforge-guild pyforge steward upgrade prove-landed --no-init
```

`prove-landed` (alias `verify`) gives one pass or fail verdict from three gates: the `bmad-drift-check` integrity result, the conda-forge-expert skill meta-tests, and a `bmad-loop validate` of each loop home.

By default it first runs `bmad-loop init` in each loop home under `~/.bmad-loops` to refresh the hook relays. That is the duty's one write outside this repository. `--no-init` skips it and only validates; an agent uses `--no-init` and leaves the relay refresh to the operator.

### 5. Reconcile what depends on the version

After the upgrade lands, regenerate the BMAD estate page with `pixi run -e pyforge-guild scribe catalog bmad-estate --write`, and re-apply any local skill edits the pre-flight listed.

## How to tell it worked

| Exit | Meaning |
| --- | --- |
| `0` | The verb ran and reported ok: a report was printed, the apply finished, or `prove-landed` passed. |
| `1` | The verb ran and reported not ok: the apply refused, or a `prove-landed` gate failed. |
| `2` | A usage error. |
| `70` | An internal error. |

The upgrade is done when the pre-flight for the new version shows it as both installed and target, `pin-fan-out` shows no `not_moved` site that steward owns, and `prove-landed` exits `0`.

## Tips

- `--apply` and `prove-landed` were not executed for this page; their behaviour is taken from `--help`, the module and the team-memory entry `.claude/memory/feedback/upgrade-bmad-core-and-the-skf-custom-module-only-through-pix.md`. The pre-flight and `pin-fan-out` were run.
- The duty never calls `scripts/bmad-switch`, and the installer stays the only writer of `_bmad/bmm/**` and `_bmad/core/**`.
- A configuration pin in `_bmad/custom/config.toml` must sit at the installer's own key path. The same key at a second path makes skill rendering halt with "ambiguous config value".
