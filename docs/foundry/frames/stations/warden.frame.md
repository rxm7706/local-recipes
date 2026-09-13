---
type: frame [0.3]
identifier: pyforge-warden
license: https://www.apache.org/licenses/LICENSE-2.0
name: pyforge-warden
description: Station Frame for Warden — sole PR-gate verdict over dependency hygiene, vulns, license, and currency. Load when scanning manifests or projecting a compliance exit code.
visibility: private
owner: warden
version: 0.1.0
scope: station
inherits: pyforge
---

# Warden

- Grammar: `warden scan` / `pyforge warden scan`. Do not import `pyforge.warden` internals.
- The CLI is the sole gate. `--doctor` never exits 1. Do not invent a second PR-gate verdict.
- Hub "Guard" language must not mint another verdict beside this one.
- Does not replace `conda-forge-expert`.
