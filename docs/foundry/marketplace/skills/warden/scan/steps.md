# Steps — @warden/scan

Run these from the project you want to scan. Verified 2026-10-21.
The 2026-10-20 paper skill card is sample data and is not this runbook.

## 1. Scan with the station command

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

**Unpublished.** `pyforge-warden` 0.1.0 and `pyforge-core` returned HTTP 404
on PyPI, conda-forge, and SelfExplainML on 2026-10-21. Until those
packages are published, step 1 does not run on a teammate machine, and
there is no substitute command that produces the compliance report.

## 2. Probe the engines, and stop there

```bash
deptry --version
osv-scanner --version
```

Verified: `deptry` 0.25.1 and `osv-scanner` 2.4.0. The warden CLI calls
`deptry` and `osv-scanner scan --offline` itself. Do not paste their output
into a review as a warden verdict.

## 3. Stop

Do not add a second gate, and do not import `pyforge.warden`.
