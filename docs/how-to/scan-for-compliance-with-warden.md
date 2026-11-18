---
sources:
  - src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/verdict.py
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md
verified: 2026-11-18
---

# How to scan for compliance with warden

Use the `warden scan` CLI to check a project's Python, conda and pixi manifests for dependency-hygiene and vulnerability problems, and to read the single status and exit code it reports.

## When to use this

- You want a compliance verdict on a project directory before a change lands.
- You are adopting the gate on a project that already has findings.
- You need the report as JSON, or a CycloneDX SBOM beside it.
- A scan gave a result you do not trust and you want to check the scanner's own environment.

## When to skip this

- You want to know whether engines and feeds are present across a checkout, with other pre-flight checks. `pyforge doctor check` wraps warden's self-check; see [How to diagnose with doctor](diagnose-with-doctor.md).

:::note
**Prerequisites.** Run from the repository root, in warden's own environment, `-e pyforge-warden`; the session default `pyforge-guild` does not carry it. `warden scan …` and `pyforge warden scan …` are the same command. Warden scans offline: the OSV database and the KEV, EPSS and end-of-life feeds must already be on disk for their axes to be assessed.
:::

:::caution[Important]
The CLI is the only publisher of the verdict. Relay its status and exit code as printed; do not import `pyforge.warden` or recompute a status yourself.
:::

## Steps

### 1. Check the scanner's environment first

```bash
pixi run -e pyforge-warden pyforge warden scan --doctor
```

`--doctor` is a flag on `scan`, not a separate command. It checks the engines, the offline OSV database and the feed caches, scans no project and uses no network:

```text
warden: doctor status=problem checks=7
  [doctor] deptry ok -- within tested range <0.26,>=0.25.1
  [doctor] osv-scanner ok -- within tested range <2.5,>=2.4.0
  [doctor] osv-db problem -- OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY is unset or empty -- no offline OSV database configured
  [doctor] kev-feed ok -- operating air-gapped: kev feed not present -- ...
```

It exits `0` when every check is healthy and `2` otherwise. It never exits `1`, because it reports on the environment, not on a project.

Run it before any scan. A scan can only assess what the environment can assess: with no OSV database the vulnerability axis is not assessed at all.

### 2. Provision what `--doctor` says is missing

| Missing | How it is provided |
| --- | --- |
| The offline OSV database | Set `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` to its root. `scripts/platform-provision-osv-offline-db.sh` provisions one. |
| The KEV, EPSS or end-of-life feed | Set `PYFORGE_WARDEN_FEED_CACHE_DIR` to the cache root. The refresh scripts under `src/shared/packages/pyforge-warden/scripts/` (`refresh_kev_feed.py`, `refresh_epss_feed.py`, `refresh_endoflife_feed.py`) fill it. |

An absent feed is reported as "operating air-gapped" and does not fail `--doctor`. An absent KEV feed still matters: the `fail-on-kev` gate is on by default, so a default scan composes `indeterminate` on the vulnerability axis until the feed is there.

The provisioning scripts fetch from the network and write caches. They are not run by a scan and were not run for this page.

### 3. Scan a project

```bash
pixi run -e pyforge-warden pyforge warden scan <path>
```

`path` defaults to the current directory. The default output is one summary line; diagnostics go to stderr.

When a `pixi.lock` holds more than one environment, warden extracts the union of top-level packages and says so. Scope the scan with `--pixi-environment NAME` and `--pixi-platform PLATFORM`.

### 4. Adopt the gate without blocking

```bash
pixi run -e pyforge-warden pyforge warden scan <path> --warn-only
```

`--warn-only` downgrades every still-blocking status (`policy-violation`, `indeterminate`) to `warn` before the verdict is composed, so findings are reported and the run exits `0`.

:::caution
A green `--warn-only` run is not a clean vulnerability verdict. With no OSV database, the vulnerability axis composes `indeterminate` findings, and `--warn-only` downgrades those like any other, leaving the axis silently unassessed. That is why step 1 comes first. An operational error still exits `2` under `--warn-only`: a manifest that cannot be parsed, or a missing engine, is never downgraded.
:::

### 5. Get the report as JSON, or an SBOM

```bash
pixi run -e pyforge-warden pyforge warden scan <path> --format json
pixi run -e pyforge-warden pyforge warden scan <path> --sbom-output <file>
```

`--format json` puts exactly one schema-valid `ComplianceReport` on stdout. `--sbom-output` also writes a CycloneDX 1.6 SBOM; a failure to write it is a stderr diagnostic and never changes the exit code.

### 6. Tighten the policy

These flags decide which findings compose which status. Each also has a key in a `[tool.pyforge-warden]` table in the scanned project's `pyproject.toml` or `pixi.toml`; a CLI flag wins over both files.

| Flag | Effect |
| --- | --- |
| `--fail-on {critical,high,medium,low,none}` | The severity at or above which a vulnerability is a `policy-violation` (default `critical`). |
| `--fail-under-coverage N` | An axis that assessed less than N percent of dependencies is `indeterminate`. |
| `--allow-licenses`, `--deny-licenses` | Turn on the license axis with an SPDX allow-list or deny-list. |
| `--max-lag N`, `--require-lts`, `--fail-on-eol` | Turn on the currency axis. |
| `--min-epss N` | A vulnerability with an EPSS score at or above N is a `policy-violation`. |
| `--warn-as-error` | A composed `warn` exits `1`. |

`--baseline PATH` suppresses the findings a committed `.warden-baseline.yaml` lists, and `--baseline-emit` prints a stanza for such a file without suppressing anything. `--bypass --reason TEXT` marks every remaining finding `bypassed` and prints a waiver stanza for a human to commit; it never writes into the scanned tree.

## How to tell it worked

Warden composes one status from seven, strongest first. The strongest status any finding reaches is the report's status, and the exit code follows from it.

| Status | Exit | Meaning |
| --- | --- | --- |
| `error` | `2` | The scan could not finish: an unparsable manifest, a missing or failed engine, a bad configuration. |
| `policy-violation` | `1` | A finding breaks the policy. |
| `indeterminate` | `1` | An axis could not be assessed, so no trusted verdict exists. |
| `warn` | `0` | Findings below the blocking threshold, or downgraded by `--warn-only`. |
| `bypassed` | `0` | Findings waived. |
| `clean` | `0` | Assessed, nothing found. |
| `not-applicable` | `0` | Nothing to assess. |

| Exit | Meaning |
| --- | --- |
| `0` | `clean`, `warn`, `bypassed` or `not-applicable`; a healthy `--doctor`. |
| `1` | `policy-violation` or `indeterminate`; a `warn` under `--warn-as-error`. |
| `2` | `error`, a usage error, or an unhealthy `--doctor`. |
| `130` | Interrupted. |

Read the exit code directly (`echo $?`), never through a pipe. `indeterminate` exits `1` on purpose: "could not check" is never reported as a pass.

## Tips

- `--allow-empty` exits `0` when manifests parse but yield nothing to assess. The status stays `indeterminate`.
- `--open-fix-prs` opens remediation pull requests through the forge API. That is outward work: an agent uses `--fix-prs-dry-run`, which plans the same proposals and opens no connection.
- The station's MCP face runs one command, `warden scan <target> --format json`. See [Reach a station's MCP endpoint](reach-a-station-mcp-endpoint.md).
- Every flag, configuration key, status, error kind and exit code is a row of the station contract, `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md`.
