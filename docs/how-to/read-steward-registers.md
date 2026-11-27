---
sources:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/budget.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/measures.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/guards.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/track.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deck_integrity.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
verified: 2026-11-27
---

# How to read steward's registers

Use steward's `budget`, `measure`, `guards`, `track` and `deck-drift` duties to read the small registers steward keeps: the declared cost ceiling, the measure catalog, the Guard library, a run's track record, and a pulled deck's integrity baseline.

## When to use this

- You need to know the declared cost ceiling, or declare one.
- You want to know which measures are published and which are switched on.
- You are writing a Spec and want to know which Guard categories it still lacks.
- You need one durable record of a finished run.
- A pulled Design deck may have been edited by hand since it was pulled.

## When to skip this

- You want story status across stations. That is `steward ledger-query`; see [How to Monitor the Fleet](monitor-the-fleet.md) § *Done / Running / Next in one call*.

:::note
**Prerequisites.** Run from the repository root in `-e pyforge-guild`. None of these duties is a detector or a PR gate: each reports, and none decides whether a change may merge.
:::

## Steps

### 1. Read or declare the cost ceiling

```bash
pixi run -e pyforge-guild pyforge steward budget show
pixi run -e pyforge-guild pyforge steward budget check
```

`show` prints the declared ceilings, or `no ceiling has ever been declared`. Add `--json` for JSON.

`check` always exits `3` in this version. Steward declares and shows a ceiling but does not meter real spend against it, so it reports "no metered spend source configured" instead of inventing a pass or a fail. Treat `3` here as "no data", not as an error.

```bash
pixi run -e pyforge-guild pyforge steward budget set --cap 1500usd/month
```

`set` writes the ceiling to `.steward/budget.yaml`. The cap has the shape `<amount><currency>/<period>`, and a malformed value is refused before the file is touched. Declaring a ceiling is a decision; set one when the operator names the figure. Every `budget` verb sits behind the kill switch `pyforge.steward.budget`.

### 2. List the measures

```bash
pixi run -e pyforge-guild pyforge steward measure list
pixi run -e pyforge-guild pyforge steward measure check
```

`list` prints every measure in the Build League catalog with its state, dimension and source:

```text
catalog 'build-league-measures' — 8 measure(s)
  detector-pass-fail: on (team) detector / detectors-ci vector
  run-cost-usd: on (agent) driver.py per-run total_cost_usd
  ...
```

`check` validates the catalog and prints `measure check: ok`. It enforces two rules: a new measure starts `off`, and an archived id is never reused. The catalog is `src/shared/packages/pyforge-steward/measures/measures.yaml`; `--measures-dir DIR` reads another directory. Add `--json` to either verb.

### 3. Read the Guard library

```bash
pixi run -e pyforge-guild pyforge steward guards catalog
pixi run -e pyforge-guild pyforge steward guards lacking
pixi run -e pyforge-guild pyforge steward guards lacking --spec <path-to-SPEC.md>
```

`catalog` prints the seven Guard categories as JSON, each with the live surfaces that implement it and whether it is in the library yet. `lacking` with no argument names the categories the library itself still lacks (today, `outcome`). With `--spec` it names the categories that Spec's `hub_guards:` list still lacks.

```bash
pixi run -e pyforge-guild pyforge steward guards source-ground --text <file>
```

`source-ground` checks that each claim in a text file carries a `[source: path]` citation that resolves. `--repo DIR` sets the root that citations resolve against (default: the current directory).

### 4. Assemble a run's track record

```bash
pixi run -e pyforge-guild pyforge steward track assemble --run-dir <dir> --out <path>/track.json
```

`assemble` reads a run directory's journal, gate record and state and writes one `track.json`. The raw run files stay where they are. Missing optional groups are written as empty, never invented. The record states its own retention: the track is kept indefinitely, the raw payload 90 days.

### 5. Check a pulled deck for silent drift

```bash
pixi run -e pyforge-guild pyforge steward deck-drift --slug <deck-slug> --path <pulled-artifact>
```

Herald pulls a Design deck and records its etag in `.herald/bridge-state.json`. `deck-drift` fingerprints the pulled file (size and hash) the first time it sees an etag and stores that in `.steward/deck-integrity-baseline.json`. On a later run, the same etag with a different fingerprint is a finding: the file changed without a new pull. A changed etag is a legitimate re-pull, and the baseline moves with it.

`--artifact-key KEY` names the etag entry to read (default `prototype`); `--bridge-state PATH` and `--baseline PATH` override the two files. The deck workflow itself is in [the presentation deck guide](presentation-deck.md).

## How to tell it worked

| Exit | Meaning |
| --- | --- |
| `0` | The duty ran and reported ok. |
| `1` | The duty ran and reported not ok: a failed `measure check`, or drift found by `deck-drift`. |
| `2` | A usage error, or a kill switch that is off. |
| `3` | `budget check`: no metered spend source is configured. |
| `70` | An internal error. |

Read the exit code directly (`echo $?`), never through a pipe.

## Tips

- `budget set`, `guards source-ground`, `track assemble` and `deck-drift` were not executed for this page, because each writes a file or needs an input that was not at hand; their behaviour is taken from `--help` and the modules. The other verbs were run.
- No Guard is a PR verdict. Warden's scan is the gate and Doctor's findings are advisory.
- Every flag and exit code is a row of the station contract, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md`.
