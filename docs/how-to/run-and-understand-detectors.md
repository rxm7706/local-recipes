---
sources:
  - scripts/detectors.py
  - pixi.toml
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py
  - docs/reference/judgement-vocabulary.md
verified: 2026-09-20
---

# How to run and understand Detectors

PyForge's detectors form the core of our CI pipeline (`detectors-ci`) and continuous governance. They are small, offline, deterministic checks that enforce invariants across the codebase.

This guide explains how to run the detector suite locally and how to interpret the results. For architecture rationale, see [The Detector Framework](../explanation/the-detector-framework.md).

## Running the Detectors

The detector registry is `scripts/detectors.py`. Run it through its pixi tasks in the `pyforge-guild` environment (the session default), which carries the `pyforge.doctor` sources the registry threads in:

```bash
pixi run -e pyforge-guild detectors          # every detector, repo + runtime scope
pixi run -e pyforge-guild detectors-ci       # the CI-safe subset (--scope repo)
pixi run -e pyforge-guild detectors -- --list   # what the registry discovered
pixi run -e pyforge-guild detectors -- --json   # machine-readable rows
```

### Filtering by Scope

Detectors are divided into two scopes:
1. `repo`: Runs anywhere, checks only tracked files. These are CI-safe.
2. `runtime`: Checks host state (e.g. `~/.bmad-loops`, `tmux` sessions, the gitignored Tier-3 sprint feeds). These cannot run in CI.

To run one scope explicitly:
```bash
pixi run -e pyforge-guild detectors -- --scope repo
pixi run -e pyforge-guild detectors -- --scope runtime
```

Each detector also has its own pixi task (`pixi task list -e pyforge-guild`, every `*-check` entry) — for example `pixi run -e pyforge-guild spec-surface-check` or `docs-map-hygiene-check`.

## Interpreting the Exit Codes

The detector registry adheres strictly to a three-tier exit code system:

| Exit Code | Status | Meaning |
|-----------|--------|---------|
| `0` | **Pass** | Every selected detector ran and passed. |
| `1` | **FINDINGS** | At least one detector reported a violation of an invariant. |
| `2` | **UNKNOWN** | At least one detector **could not run** (e.g., timed out, threw an exception, or a dependency like `pyforge.doctor` was unimportable), and no detector reported findings. |

> [!WARNING]
> **Exit code 2 is not a softer 0.** A detector that cannot run reports `unknown`, which is never green. The dashboard status strip will not claim "green" if it could not measure the metric.

> [!WARNING]
> **A single Doctor-sourced task uses a different exit domain.** `spec-surface-check`, `story-status-check`, `docs-map-hygiene-check` and the other `python -m pyforge.doctor.sources <name>` tasks project through `pyforge.doctor.verdict.exit_code_for`: any `fail` finding exits `2`, and a `warn` finding never changes the exit code (`0`). So `2` from the registry means "could not run" while `2` from one source means "failed" — read the finding rows, and always read the exit code directly, never through a pipe (a pipe reports the last command's status). The full domain table is in [`judgement-vocabulary.md`](../reference/judgement-vocabulary.md) § *Severity and exit codes*.

## Remediating Common Findings

If the suite exits with `1` (FINDINGS), read the output block at the end of the script's execution.

### Registry Gaps
A registry gap occurs if a script looks like a detector (`scripts/*_check.py` or `docs/dashboard/check_*.py`) but is not wired properly.
- **Fix:** Declare its scope at module level — `DETECTOR = {"scope": "repo"}` or `{"scope": "runtime"}` (`DETECTOR = None` opts a residual mutation-only script out) — and map the script to a pixi task in `pixi.toml` (e.g. `[feature.guild-tasks.tasks.my-detector-check]`).

### Spec Surface Drift (`spec-surface-check`)
This occurs when a governed file is added or modified, but the owning Spec's `.memlog.md` did not record the event.
- **Fix:** See [How to reconcile spec surface drift](reconcile-spec-surface.md).

### Chain Sprawl (`chain-sprawl-check`)
This occurs if you create a standalone Dream/Spec pair that violates the 1:1 "one chain per station" rule, without an explicit `fold-exemption`.
- **Fix:** Either fold the capability into an existing station's Spec, or add an exemption if it is truly cross-cutting (e.g., the testing kit). See [One-Chain Station Ops](one-chain-station-ops.md).

### Fold complete (`fold-complete-check`)
An archived Dream under `archive/docs/dreams/` has a paragraph that is not in its station Dream (`docs/dreams/pyforge-<owner>.md`). The check splits the archived body into paragraphs (blank-line separated, frontmatter and heading lines left out, whitespace collapsed, only those longer than 80 characters) and fails naming the file and how many are missing (`fold-complete-incomplete`). An `owner:` that is missing, unparseable, or not a station slug fails (`fold-complete-no-owner`), and so does an owner whose station Dream is absent (`fold-complete-no-station-dream`). Files listed in `docs/governance/fold-complete-baseline.json` are not folds of a station Dream and are never read. The same run raises one warning counting the Dreams in `docs/dreams/` that still read `status: archived`, per station; that is the migration's countdown, never a failure; Dreams whose frontmatter cannot be read (a glued `---title:` opener) have no status to count, so the warning adds "N more have unreadable frontmatter (status unknown)" and still fires when only those remain. A missing or unreadable `docs/governance/fold-complete-baseline.json` raises the single warning `fold-complete-no-baseline` and nothing else is judged. Each passing Dream gets an OK naming it (`fold-complete-ok`), each baselined one an OK saying it was not read (`fold-complete-baselined`).
- **Fix:** paste the satellite's whole body, verbatim, into a dated section of the station Dream, with its headings demoted one level, then `git mv` the file to `archive/docs/dreams/`. Heading depth does not matter to the check. A leftover `Consolidated into` banner counts as a missing paragraph, because CHAIN-STANDARD section 7 item 4 says a moved Dream carries none. Never add a path to the baseline to clear a finding. See CHAIN-STANDARD section 11.

### Docs map hygiene (`docs-map-hygiene-check`)
A page under `docs/tutorials`, `docs/how-to`, `docs/reference` or `docs/explanation` is not linked from `docs/MAP.md` (fail — promoted from warn by Story 30.2/CAP-84), or the map links a page under `docs/` that does not exist (fail).
- **Fix:** Add the page to the right quadrant table in `docs/MAP.md`, or repoint/remove the dead link.

### Docs currency (`docs-currency-check`)
Three checks over `docs/map.yaml` (the registry) and `docs/MAP.md` (its render): `map-render` (the generated `## Page registry` section is stale against a fresh render of `docs/map.yaml`), `authored-page-stale` (a `kind: authored` page's own `sources:`/`verified:` frontmatter has fallen behind a named source's git last-touch, or a named source has no git history at all, or the page body cites a backticked skill/script/path token that no longer resolves), `skill-dir-hygiene` (a stray `README.md` inside a managed `bmad-*`/`pyforge-*`/`skf-*` skill directory). All three warn-only, fail-open.
- **Fix (map-render):** run `pixi run -e pyforge-guild docs-map-render` to regenerate the section from `docs/map.yaml`.
- **Fix (authored-page-stale):** after confirming the page's claims still hold against the named source's current content, bump its frontmatter `verified:` date; for a dead body reference, fix the token, or — when it is a deliberate historical citation — wrap it in `<!-- governance-currency:ignore-start (reason) --> ... <!-- governance-currency:ignore-end -->`.
- **Fix (skill-dir-hygiene):** remove the stray file; nothing outside the Agent Skills layout belongs in a managed skill directory.
