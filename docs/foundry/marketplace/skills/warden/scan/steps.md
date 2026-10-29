# Steps — @warden/scan

Run these from the project you want to scan. Verified 2026-10-21 against
`warden scan --help` and the tools on the verifying host. Each version below
is what that tool's `--version` printed on that host on 2026-10-21.

**Before you start.** `pyforge-warden` 0.1.0 and `pyforge-core` returned HTTP
404 on PyPI, conda-forge, and SelfExplainML on 2026-10-21. Step 1 waits on
those packages, and no published command produces the compliance report in
its place. Steps 0 and 2 run today; they produce probes, not a report.

## 0. Install the published tools

- `deptry` 0.25.1: `pip install deptry` (PyPI `deptry`) or
  `conda install -c conda-forge deptry`.
- `osv-scanner` 2.4.0: `conda install -c conda-forge osv-scanner`, or the
  binary from the osv-scanner GitHub release page.

## 1. Scan with the station command (waits on `pyforge-warden`)

When `pyforge-warden` is on your `PATH`:

```bash
warden scan .
```

The same argv through dispatch:

```bash
pyforge warden scan .
```

Environment self-check, not a scan:

```bash
warden scan --doctor
```

`--doctor` exits 0 or 2, never 1. Verified: `warden scan --help` lists
`--doctor` on `scan`.

## 2. Probe the engines, and stop there

```bash
deptry --version
osv-scanner --version
```

`deptry` and `osv-scanner` are not a warden verdict. The warden CLI calls
`deptry` and `osv-scanner scan --offline` itself. Do not paste their output
into a review as a warden verdict.

## 3. Stop

Nothing else runs from this runbook.
