# Steps — @warden/scan

Run these from the project you want to scan. Verified 2026-10-21 against
`warden scan --help` and the tools on the verifying host. Each version below
is what that tool's `--version` printed on that host on 2026-10-21.

**Before you start.** `pyforge-warden` 0.1.0 and `pyforge-core` returned HTTP
404 on PyPI, conda-forge, and SelfExplainML on 2026-10-21. Step 1 waits on
those packages, and no published command produces the compliance report in
its place. Steps 0 and 2 run today; they produce probes, not a report.

## 0. Install the published tools

Install both in the ranges `pyforge-warden` pins for its engines, so the
versions you probe are the ones warden accepts once it is published.
`osv-scanner` 2.5 or later (conda-forge served 2.7.0 on 2026-10-29) is outside
that range.

- `deptry` 0.25.1, range `>=0.25.1,<0.26`: `pip install "deptry>=0.25.1,<0.26"`
  (PyPI `deptry`) or `conda install -c conda-forge "deptry>=0.25.1,<0.26"`.
- `osv-scanner` 2.4.0, range `>=2.4.0,<2.5`:
  `conda install -c conda-forge "osv-scanner>=2.4.0,<2.5"`, or the v2.4.0
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
