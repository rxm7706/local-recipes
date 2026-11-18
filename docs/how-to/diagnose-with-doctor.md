---
sources:
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/verdict.py
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/contract.md
verified: 2026-11-17
---

# How to diagnose with doctor

Use the `pyforge doctor` CLI to check that a checkout can run its scanners, watch the fleet's package health, and get a ranked prescription for one feedstock or maintainer.

## When to use this

- Before a scan or a session, to see whether the engines and feeds it depends on are present.
- To look for stale or vulnerable packages across the fleet.
- To ask "what is wrong with this one package, and what should I do first?"
- To find deferred work that names an epic or story before you start it.

## When to skip this

- You want the planning detectors (`spec-surface-check`, `story-status-check` and the rest). They are Doctor sources run one at a time; see [How to run and understand Detectors](run-and-understand-detectors.md).
- You want a compliance verdict on dependencies. That is warden's; see [How to scan for compliance with warden](scan-for-compliance-with-warden.md).

> [!NOTE]
> **Prerequisites.** Run from the repository root. `pyforge-guild` carries doctor, but not warden, so the engine checks need `-e pyforge-doctor`. `monitor` and `diagnose` read conda-forge-expert's `cf_atlas.db`; on a checkout that has never built it (the `build-cf-atlas` task), both report that the signal is unavailable.

> [!IMPORTANT]
> Doctor reports whether things can run, not whether a change may merge. Its findings are advisory. A Doctor exit code is never a second PR verdict.

## Steps

### 1. Run the pre-flight check

```bash
pixi run -e pyforge-doctor pyforge doctor check
```

With no flags, `check` runs the engine checks (warden's own self-check), the environment-hygiene scan and the ledger-durability check against the current directory, and prints one line per finding:

```text
doctor check: 10 finding(s) -- 7 ok, 2 warn, 1 fail
  [warden-doctor] deptry: ok -- within tested range <0.26,>=0.25.1
  [warden-doctor] osv-db: fail -- OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY is unset or empty -- no offline OSV database configured
  [env-hygiene] unconditional-credential-injection: warn -- ...
  [marshal-durability] marshal-durability-regression: ok -- 8 tracked ledger(s) hold every completion they held at HEAD
```

Each line reads `[source] check: status -- message`. The counts in the first line will differ on your machine.

Narrow the run with these flags:

| Flag | Effect |
| --- | --- |
| `--list` | Print the check catalog and run nothing. |
| `--engines [NAME]`, `--env [NAME]` | Run one category, or one named check in it. |
| `--durability` | Run only the ledger-durability category. |
| `--bmad-core`, `--sibling-dreams` | Opt-in categories that call the network; never part of the default run. |
| `--scope repo` | Only categories that read tracked files and git history. |
| `path` | Check another directory instead of the current one. |

### 2. Watch the fleet

```bash
pixi run -e pyforge-guild pyforge doctor monitor --fleet
pixi run -e pyforge-guild pyforge doctor monitor --fleet --watch staleness,cve,abandonment
pixi run -e pyforge-guild pyforge doctor monitor --fleet --target <maintainer>
```

`--fleet` is required; without it the command is a usage error. `--watch` takes a comma-separated list from `staleness`, `cve`, `abandonment`, `adoption` and `behind-upstream`, and defaults to `staleness,cve`. `--target` scopes every axis to one maintainer or feedstock. `--source` filters the output to one source tag. `--surface PATH` also writes a fleet-health file to `PATH`, so leave it off for a read-only look.

### 3. Diagnose one target

```bash
pixi run -e pyforge-guild pyforge doctor diagnose --target <feedstock-or-maintainer>
```

This gathers the fleet signals for one name and reports them. When the target is also an existing local directory, the engine and environment checks run against it too.

### 4. Ask for a prescription

```bash
pixi run -e pyforge-guild pyforge doctor diagnose --target <feedstock-or-maintainer> --prescribe
```

`--prescribe` partitions the findings, ranks them and names a root cause for each. Without it, findings are reported but never ranked. The output adds a grade and a numbered list:

```text
doctor diagnose: 2 finding(s) -- 0 ok, 0 warn, 2 fail
  grade: incomplete -- gather did not complete for axis(es): cve-watcher, staleness-report
  ...
  2 prescription(s):
    [actionable, rank 1] staleness-report:doctor.sources.atlas: address doctor.sources.atlas (staleness-report)
      root cause: ...
      safe upgrade: none -- no upstream target version available in this Finding's evidence
```

Read a prescription from the top: rank 1 is the one to act on first. `root cause` says why the finding exists. `safe upgrade` names a target version when the evidence holds one, and otherwise says why there is none. A grade of `incomplete` means an axis could not be gathered, so the report measured nothing on it; fix the gather before you trust the rest.

### 5. Get the report as JSON

Add `--json` to `check`, `monitor`, `diagnose` or `backlog-intake`. Stdout then carries one schema-valid `DoctorReport` document. Its `findings` entries have `source`, `check`, `status`, `message` and `evidence`. A `diagnose --prescribe` report also carries `grade`, `axis_scores` and `prescriptions`, where each prescription has `rank`, `partition`, `action`, `root_cause`, `safe_upgrade_target` and `safe_upgrade_reason`.

### 6. Find deferred work before you start a story

```bash
pixi run -e pyforge-guild pyforge doctor backlog-intake 13.1
```

The identifier is an epic (`13`) or a story (`13.1` or `13-1`). The command scans every station's tracked `deferred-work-ledger.md` and reports each entry that names it as a `warn` finding, so the exit code stays `0`.

## How to tell it worked

| Exit | Meaning |
| --- | --- |
| `0` | No `fail` finding. A `warn` never changes the exit code. |
| `2` | At least one `fail` finding, a usage error, or a refused actuator. |
| `130` | Interrupted. |

Doctor never exits `1`. Read the exit code directly (`echo $?`), never through a pipe. The `0`/`1`/`2` codes of the detector registry belong to `scripts/detectors.py`, not to Doctor; [`judgement-vocabulary.md`](../reference/judgement-vocabulary.md) § *Severity and exit codes* keeps the two apart.

## Tips

- `doctor check` in `-e pyforge-guild` exits `2` with one `pyforge-warden not installed` finding, because that environment has no warden. Use `-e pyforge-doctor` for the engine checks.
- `doctor flags kill-switch --flag KEY --reason TEXT` is Doctor's one command that writes: it disables a feature flag in the flag tree. Run it only when the operator asks.
- The station's MCP face runs one verb, `doctor diagnose --target <target> --json`. See [Reach a station's MCP endpoint](reach-a-station-mcp-endpoint.md).
- Every verb, option, check code and exit code is a row of the station contract, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/contract.md`.
- For why detectors and Doctor sources are built this way, see [The Detector Framework](../explanation/the-detector-framework.md).
